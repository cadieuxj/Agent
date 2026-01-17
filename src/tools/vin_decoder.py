"""VIN Decoder Tool using NHTSA vPIC API."""
import httpx
from typing import Dict, Optional
from pydantic import BaseModel, Field


class VinDecodeResult(BaseModel):
    """VIN decode result model."""

    vin: str
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    brake_system_type: Optional[str] = None
    primary_fuel_type: Optional[str] = None
    body_class: Optional[str] = None
    gvwr_class: Optional[str] = None
    manufacturer: Optional[str] = None
    plant_city: Optional[str] = None
    plant_country: Optional[str] = None
    error_code: Optional[str] = None
    error_text: Optional[str] = None
    raw_data: Optional[Dict] = Field(default_factory=dict)


class VinDecoderTool:
    """Tool to decode VINs using NHTSA vPIC API.

    This tool queries the NHTSA Vehicle Product Information Catalog (vPIC) API
    to retrieve detailed vehicle information including:
    - Brake System Type
    - Primary Fuel Type
    - GVWR Class
    - Body Class
    - Manufacturer details
    """

    BASE_URL = "https://vpic.nhtsa.dot.gov/api/vehicles"

    def __init__(self, timeout: float = 10.0):
        """Initialize the VIN decoder tool.

        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout

    async def decode_vin(self, vin: str) -> VinDecodeResult:
        """Decode a VIN using the NHTSA vPIC API.

        Args:
            vin: Vehicle Identification Number (17 characters)

        Returns:
            VinDecodeResult containing decoded vehicle information
        """
        if not vin or len(vin) != 17:
            return VinDecodeResult(
                vin=vin,
                error_code="INVALID_VIN",
                error_text=f"Invalid VIN length: {len(vin) if vin else 0}. Expected 17 characters."
            )

        url = f"{self.BASE_URL}/DecodeVin/{vin}?format=json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

                # Parse the results
                results = data.get("Results", [])
                if not results:
                    return VinDecodeResult(
                        vin=vin,
                        error_code="NO_DATA",
                        error_text="No data returned from vPIC API"
                    )

                # Extract specific fields
                decoded_data = self._parse_vpic_results(results)
                decoded_data["vin"] = vin
                decoded_data["raw_data"] = {r["Variable"]: r["Value"] for r in results if r.get("Value")}

                return VinDecodeResult(**decoded_data)

        except httpx.TimeoutException:
            return VinDecodeResult(
                vin=vin,
                error_code="TIMEOUT",
                error_text=f"Request timeout after {self.timeout} seconds"
            )
        except httpx.HTTPStatusError as e:
            return VinDecodeResult(
                vin=vin,
                error_code="HTTP_ERROR",
                error_text=f"HTTP {e.response.status_code}: {str(e)}"
            )
        except Exception as e:
            return VinDecodeResult(
                vin=vin,
                error_code="UNKNOWN_ERROR",
                error_text=str(e)
            )

    def _parse_vpic_results(self, results: list) -> Dict:
        """Parse vPIC API results into structured data.

        Args:
            results: List of result dictionaries from vPIC API

        Returns:
            Dictionary of parsed vehicle attributes
        """
        field_mapping = {
            "Make": "make",
            "Model": "model",
            "Model Year": "year",
            "Brake System Type": "brake_system_type",
            "Fuel Type - Primary": "primary_fuel_type",
            "Body Class": "body_class",
            "GVWR": "gvwr_class",
            "Gross Vehicle Weight Rating From": "gvwr_class",
            "Manufacturer Name": "manufacturer",
            "Plant City": "plant_city",
            "Plant Country": "plant_country",
        }

        parsed = {}
        for result in results:
            variable = result.get("Variable")
            value = result.get("Value")

            if not value or value == "Not Applicable":
                continue

            if variable in field_mapping:
                field_name = field_mapping[variable]

                # Convert year to int
                if field_name == "year":
                    try:
                        parsed[field_name] = int(value)
                    except (ValueError, TypeError):
                        continue
                else:
                    parsed[field_name] = value

        return parsed

    async def decode_vin_batch(self, vins: list[str]) -> list[VinDecodeResult]:
        """Decode multiple VINs.

        Args:
            vins: List of VINs to decode

        Returns:
            List of VinDecodeResult objects
        """
        results = []
        for vin in vins:
            result = await self.decode_vin(vin)
            results.append(result)
        return results

    def get_description(self) -> str:
        """Get tool description for agent framework."""
        return """Decode a Vehicle Identification Number (VIN) to retrieve detailed vehicle information.

This tool queries the NHTSA vPIC API to extract:
- Brake System Type (e.g., Hydraulic, Air, Hydraulic with ABS)
- Primary Fuel Type (e.g., Gasoline, Diesel, Electric, CNG)
- GVWR Class (Gross Vehicle Weight Rating)
- Body Class (e.g., Truck, Van, Cargo Van)
- Manufacturer details and plant information

Input: A 17-character VIN
Output: Structured vehicle information"""

    def get_parameters_schema(self) -> Dict:
        """Get JSON schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "vin": {
                    "type": "string",
                    "description": "17-character Vehicle Identification Number",
                    "minLength": 17,
                    "maxLength": 17,
                    "pattern": "^[A-HJ-NPR-Z0-9]{17}$"
                }
            },
            "required": ["vin"]
        }


# Example usage
async def main():
    """Example usage of VinDecoderTool."""
    decoder = VinDecoderTool()

    # Example VINs (these are sample VINs for testing)
    test_vins = [
        "1HGBH41JXMN109186",  # Honda
        "5XYKT3A69CG276371",  # Hyundai
        "1FTFW1E84DFC10312",  # Ford F-150
    ]

    print("VIN Decoder Tool - Testing\n")
    for vin in test_vins:
        result = await decoder.decode_vin(vin)
        print(f"VIN: {result.vin}")
        if result.error_code:
            print(f"  Error: {result.error_text}")
        else:
            print(f"  Make: {result.make}")
            print(f"  Model: {result.model}")
            print(f"  Year: {result.year}")
            print(f"  Brake System: {result.brake_system_type}")
            print(f"  Fuel Type: {result.primary_fuel_type}")
            print(f"  GVWR Class: {result.gvwr_class}")
            print(f"  Body Class: {result.body_class}")
        print()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

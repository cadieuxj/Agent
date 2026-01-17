"""Sales Agent with Text-to-SQL for inventory queries."""
import re
from typing import List, Dict, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel


class InventoryQuery(BaseModel):
    """Structured inventory query."""

    make: Optional[str] = None
    model: Optional[str] = None
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    gvwr_class: Optional[str] = None
    body_class: Optional[str] = None
    fuel_type: Optional[str] = None


class SalesAgent:
    """Sales agent that uses Text-to-SQL to query vehicle inventory.

    This agent:
    1. Parses natural language queries
    2. Converts them to SQL queries
    3. Executes queries against the SQLite database
    4. Formats results in a user-friendly way
    """

    def __init__(self, database_url: str):
        """Initialize sales agent.

        Args:
            database_url: SQLite database URL
        """
        self.database_url = database_url
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def parse_query(self, user_query: str) -> InventoryQuery:
        """Parse natural language query into structured format.

        Args:
            user_query: Natural language query from user

        Returns:
            InventoryQuery object
        """
        query_lower = user_query.lower()
        parsed = InventoryQuery()

        # Extract make
        makes = ["ford", "chevrolet", "gmc", "ram", "toyota", "nissan", "isuzu", "freightliner", "international"]
        for make in makes:
            if make in query_lower:
                parsed.make = make.title()
                break

        # Extract model keywords
        models = {
            "f-150": "F-150",
            "f-250": "F-250",
            "f-350": "F-350",
            "silverado": "Silverado",
            "sierra": "Sierra",
            "transit": "Transit",
            "sprinter": "Sprinter",
            "promaster": "ProMaster",
            "express": "Express",
            "savana": "Savana",
        }
        for keyword, model_name in models.items():
            if keyword in query_lower:
                parsed.model = model_name
                break

        # Extract year range
        year_match = re.search(r"(\d{4})", query_lower)
        if year_match:
            year = int(year_match.group(1))
            parsed.year_min = year
            parsed.year_max = year

        year_range = re.search(r"(\d{4})\s*(?:to|-|à)\s*(\d{4})", query_lower)
        if year_range:
            parsed.year_min = int(year_range.group(1))
            parsed.year_max = int(year_range.group(2))

        # Extract price range
        price_pattern = r"(?:under|moins de|below|sous)\s*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)"
        price_match = re.search(price_pattern, query_lower)
        if price_match:
            price_str = price_match.group(1).replace(",", "")
            parsed.price_max = float(price_str)

        price_range_pattern = r"\$?(\d+(?:,\d{3})*)\s*(?:to|-|à)\s*\$?(\d+(?:,\d{3})*)"
        price_range = re.search(price_range_pattern, query_lower)
        if price_range:
            parsed.price_min = float(price_range.group(1).replace(",", ""))
            parsed.price_max = float(price_range.group(2).replace(",", ""))

        # Extract GVWR class
        gvwr_patterns = {
            r"class\s*[234567]": lambda m: f"Class {m.group(0)[-1]}",
            r"classe\s*[234567]": lambda m: f"Class {m.group(0)[-1]}",
            r"(light|léger)": "Class 2",
            r"(medium|moyen)": "Class 4",
            r"(heavy|lourd)": "Class 6",
        }
        for pattern, gvwr_value in gvwr_patterns.items():
            match = re.search(pattern, query_lower)
            if match:
                parsed.gvwr_class = gvwr_value if isinstance(gvwr_value, str) else gvwr_value(match)
                break

        # Extract body class
        body_types = {
            "truck": "Truck",
            "camion": "Truck",
            "van": "Van",
            "fourgon": "Van",
            "cargo van": "Cargo Van",
            "dump": "Dump Truck",
            "benne": "Dump Truck",
            "flatbed": "Flatbed",
            "plateau": "Flatbed",
        }
        for keyword, body_type in body_types.items():
            if keyword in query_lower:
                parsed.body_class = body_type
                break

        # Extract fuel type
        fuel_types = {
            "diesel": "Diesel",
            "gas": "Gasoline",
            "gasoline": "Gasoline",
            "essence": "Gasoline",
            "electric": "Electric",
            "électrique": "Electric",
            "hybrid": "Hybrid",
            "hybride": "Hybrid",
        }
        for keyword, fuel_type in fuel_types.items():
            if keyword in query_lower:
                parsed.fuel_type = fuel_type
                break

        return parsed

    def build_sql_query(self, query: InventoryQuery) -> str:
        """Build SQL query from structured query.

        Args:
            query: InventoryQuery object

        Returns:
            SQL query string
        """
        conditions = []
        params = {}

        if query.make:
            conditions.append("make = :make")
            params["make"] = query.make

        if query.model:
            conditions.append("model LIKE :model")
            params["model"] = f"%{query.model}%"

        if query.year_min:
            conditions.append("year >= :year_min")
            params["year_min"] = query.year_min

        if query.year_max:
            conditions.append("year <= :year_max")
            params["year_max"] = query.year_max

        if query.price_min:
            conditions.append("price >= :price_min")
            params["price_min"] = query.price_min

        if query.price_max:
            conditions.append("price <= :price_max")
            params["price_max"] = query.price_max

        if query.gvwr_class:
            conditions.append("gvwr_class LIKE :gvwr_class")
            params["gvwr_class"] = f"%{query.gvwr_class}%"

        if query.body_class:
            conditions.append("body_class LIKE :body_class")
            params["body_class"] = f"%{query.body_class}%"

        if query.fuel_type:
            conditions.append("primary_fuel_type LIKE :fuel_type")
            params["fuel_type"] = f"%{query.fuel_type}%"

        sql = "SELECT * FROM vehicles"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY price ASC LIMIT 10"

        return sql, params

    async def search_inventory(self, user_query: str) -> List[Dict]:
        """Search inventory based on natural language query.

        Args:
            user_query: Natural language query

        Returns:
            List of matching vehicles
        """
        # Parse query
        parsed_query = await self.parse_query(user_query)

        # Build SQL
        sql, params = self.build_sql_query(parsed_query)

        # Execute query
        async with self.async_session() as session:
            result = await session.execute(text(sql), params)
            rows = result.fetchall()

            vehicles = []
            for row in rows:
                vehicle = {
                    "id": row.id,
                    "make": row.make,
                    "model": row.model,
                    "year": row.year,
                    "price": row.price,
                    "gvwr_class": row.gvwr_class,
                    "body_class": row.body_class,
                    "fuel_type": row.primary_fuel_type,
                    "vin": row.vin,
                }
                vehicles.append(vehicle)

            return vehicles

    def format_results(self, vehicles: List[Dict], language: str = "fr-CA") -> str:
        """Format search results for user.

        Args:
            vehicles: List of vehicle dictionaries
            language: Output language

        Returns:
            Formatted response string
        """
        if not vehicles:
            if language == "fr-CA":
                return "Désolé, je n'ai trouvé aucun véhicule correspondant à vos critères. Voulez-vous élargir votre recherche?"
            else:
                return "Sorry, I couldn't find any vehicles matching your criteria. Would you like to broaden your search?"

        if language == "fr-CA":
            response = f"J'ai trouvé {len(vehicles)} véhicule(s) pour vous:\n\n"
            for i, v in enumerate(vehicles, 1):
                response += f"{i}. {v['year']} {v['make']} {v['model']}\n"
                response += f"   Prix: {v['price']:,.2f} $\n"
                if v.get("gvwr_class"):
                    response += f"   Classe PNBV: {v['gvwr_class']}\n"
                if v.get("body_class"):
                    response += f"   Type: {v['body_class']}\n"
                response += "\n"
            response += "Voulez-vous plus d'informations sur l'un de ces véhicules?"
        else:
            response = f"I found {len(vehicles)} vehicle(s) for you:\n\n"
            for i, v in enumerate(vehicles, 1):
                response += f"{i}. {v['year']} {v['make']} {v['model']}\n"
                response += f"   Price: ${v['price']:,.2f}\n"
                if v.get("gvwr_class"):
                    response += f"   GVWR Class: {v['gvwr_class']}\n"
                if v.get("body_class"):
                    response += f"   Body Type: {v['body_class']}\n"
                response += "\n"
            response += "Would you like more information about any of these vehicles?"

        return response

    async def handle_query(self, user_query: str, language: str = "fr-CA") -> str:
        """Handle complete sales query.

        Args:
            user_query: Natural language query
            language: Response language

        Returns:
            Formatted response
        """
        vehicles = await self.search_inventory(user_query)
        return self.format_results(vehicles, language)

    async def close(self):
        """Close database connections."""
        await self.engine.dispose()


# Example usage
async def main():
    """Example sales agent usage."""
    from src.config.settings import settings

    agent = SalesAgent(database_url=settings.database_url)

    test_queries = [
        ("Je cherche un Ford F-150 de 2020 à moins de 40000$", "fr-CA"),
        ("Show me diesel trucks under $50,000", "en-US"),
        ("Camions classe 4 disponibles", "fr-CA"),
        ("Cargo vans for delivery", "en-US"),
    ]

    print("Sales Agent - Text-to-SQL Test\n")
    for query, language in test_queries:
        print(f"Query: {query}")
        print(f"Language: {language}\n")

        # Parse query
        parsed = await agent.parse_query(query)
        print(f"Parsed: {parsed}")

        # Build SQL
        sql, params = agent.build_sql_query(parsed)
        print(f"SQL: {sql}")
        print(f"Params: {params}\n")

        # Note: Actual search would require database to be populated
        print("-" * 80 + "\n")

    await agent.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

"""Vehicle CSV ingestion script for SQLite database."""
import asyncio
import pandas as pd
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.models.vehicle import Base, Vehicle
from src.config.settings import settings


class VehicleIngestion:
    """Handles ingestion of vehicle data from CSV to SQLite."""

    def __init__(self, db_url: Optional[str] = None):
        """Initialize the ingestion handler.

        Args:
            db_url: Database URL (defaults to settings)
        """
        self.db_url = db_url or settings.database_url
        self.engine = create_async_engine(self.db_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def create_tables(self):
        """Create database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✓ Database tables created")

    async def ingest_csv(self, csv_path: str, batch_size: int = 1000):
        """Ingest vehicle data from CSV file.

        Args:
            csv_path: Path to the CSV file
            batch_size: Number of records to insert per batch
        """
        print(f"Reading CSV file: {csv_path}")

        # Read CSV with pandas
        try:
            df = pd.read_csv(csv_path)
        except FileNotFoundError:
            print(f"Error: CSV file not found at {csv_path}")
            return
        except Exception as e:
            print(f"Error reading CSV: {e}")
            return

        print(f"Found {len(df)} records in CSV")

        # Column mapping (adjust based on actual CSV structure)
        column_mapping = {
            "Make": "make",
            "Model": "model",
            "Year": "year",
            "Price": "price",
            "GVWR": "gvwr_class",
            "VIN": "vin",
            "Body Class": "body_class",
            "Trim": "trim",
            "Transmission": "transmission",
            "Drive Type": "drive_type",
            "Engine": "engine",
            "Exterior Color": "color_exterior",
            "Interior Color": "color_interior",
            "Mileage": "mileage",
            "Condition": "condition",
            "Description": "description",
        }

        # Rename columns based on mapping
        df_renamed = df.rename(columns=column_mapping)

        # Ensure required columns exist
        required_cols = ["make", "model", "year", "price"]
        for col in required_cols:
            if col not in df_renamed.columns:
                # Try to find alternative column names
                if col == "make" and "Make" in df.columns:
                    df_renamed["make"] = df["Make"]
                elif col == "model" and "Model" in df.columns:
                    df_renamed["model"] = df["Model"]
                elif col == "year" and "Year" in df.columns:
                    df_renamed["year"] = df["Year"]
                elif col == "price" and "Price" in df.columns:
                    df_renamed["price"] = df["Price"]
                else:
                    print(f"Warning: Required column '{col}' not found in CSV")
                    # Use placeholder data for missing columns
                    if col == "make":
                        df_renamed["make"] = "Unknown"
                    elif col == "model":
                        df_renamed["model"] = "Unknown"
                    elif col == "year":
                        df_renamed["year"] = 2020
                    elif col == "price":
                        df_renamed["price"] = 0.0

        # Clean data
        df_renamed = df_renamed.fillna("")

        # Convert year to int
        if "year" in df_renamed.columns:
            df_renamed["year"] = pd.to_numeric(df_renamed["year"], errors="coerce").fillna(2020).astype(int)

        # Convert price to float
        if "price" in df_renamed.columns:
            df_renamed["price"] = pd.to_numeric(df_renamed["price"], errors="coerce").fillna(0.0)

        # Insert in batches
        total_inserted = 0
        async with self.async_session() as session:
            for i in range(0, len(df_renamed), batch_size):
                batch = df_renamed.iloc[i:i + batch_size]
                vehicles = []

                for _, row in batch.iterrows():
                    vehicle_data = {}
                    for col in df_renamed.columns:
                        if col in [c.name for c in Vehicle.__table__.columns]:
                            value = row[col]
                            # Skip empty strings for optional fields
                            if value == "" and col not in required_cols:
                                continue
                            vehicle_data[col] = value

                    vehicles.append(Vehicle(**vehicle_data))

                session.add_all(vehicles)
                await session.commit()
                total_inserted += len(vehicles)
                print(f"Inserted {total_inserted}/{len(df_renamed)} records")

        print(f"✓ Successfully ingested {total_inserted} vehicles")

    async def get_vehicle_count(self) -> int:
        """Get total vehicle count in database."""
        async with self.async_session() as session:
            result = await session.execute("SELECT COUNT(*) FROM vehicles")
            count = result.scalar()
            return count

    async def close(self):
        """Close database connections."""
        await self.engine.dispose()


async def main():
    """Main ingestion function."""
    import argparse

    parser = argparse.ArgumentParser(description="Ingest vehicle CSV data into SQLite")
    parser.add_argument(
        "--csv",
        type=str,
        default="./data/inventory/Large_Car_Dataset.csv",
        help="Path to CSV file"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for insertion"
    )
    parser.add_argument(
        "--recreate-db",
        action="store_true",
        help="Drop and recreate database tables"
    )

    args = parser.parse_args()

    ingestion = VehicleIngestion()

    try:
        # Create tables
        if args.recreate_db:
            print("Recreating database tables...")
        await ingestion.create_tables()

        # Ingest CSV
        await ingestion.ingest_csv(args.csv, args.batch_size)

        # Verify
        count = await ingestion.get_vehicle_count()
        print(f"\nTotal vehicles in database: {count}")

    finally:
        await ingestion.close()


if __name__ == "__main__":
    asyncio.run(main())

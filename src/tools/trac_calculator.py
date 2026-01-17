"""TRAC Lease Calculator Tool.

TRAC (Terminal Rental Adjustment Clause) Lease Calculator
Formula: P_rent = (C_adj + R) × MF

Where:
- P_rent = Monthly rental payment
- C_adj = Adjusted capitalized cost (vehicle price - down payment)
- R = Residual value (estimated value at end of lease)
- MF = Money factor (interest rate / 2400)
"""
from typing import Dict, Optional
from pydantic import BaseModel, Field


class TRACLeaseCalculation(BaseModel):
    """TRAC lease calculation result."""

    vehicle_price: float = Field(description="Vehicle purchase price")
    down_payment: float = Field(default=0.0, description="Down payment amount")
    residual_value: float = Field(description="Estimated residual value at end of lease")
    annual_interest_rate: float = Field(description="Annual interest rate (as percentage)")
    term_months: int = Field(description="Lease term in months")

    adjusted_capitalized_cost: float = Field(default=0.0, description="C_adj = price - down payment")
    money_factor: float = Field(default=0.0, description="MF = interest rate / 2400")
    monthly_payment: float = Field(default=0.0, description="Monthly lease payment")
    total_payments: float = Field(default=0.0, description="Total of all payments")
    residual_risk: float = Field(default=0.0, description="Residual value risk exposure")

    warnings: list[str] = Field(default_factory=list, description="Important warnings")


class CalculateTracLeaseTool:
    """Tool to calculate TRAC lease payments.

    TRAC leases are open-ended, meaning:
    - The lessee bears the residual value risk
    - If actual value < residual value at end, lessee pays the difference
    - If actual value > residual value, lessee receives the difference
    - Common for commercial vehicles with high usage
    """

    def __init__(self):
        """Initialize TRAC calculator."""
        self.default_residual_percentage = 0.40  # 40% residual for commercial vehicles
        self.typical_commercial_apr = 0.06  # 6% APR typical for commercial leases

    def calculate(
        self,
        vehicle_price: float,
        down_payment: float = 0.0,
        residual_value: Optional[float] = None,
        annual_interest_rate: Optional[float] = None,
        term_months: int = 36,
        residual_percentage: Optional[float] = None,
    ) -> TRACLeaseCalculation:
        """Calculate TRAC lease payment.

        Args:
            vehicle_price: Vehicle purchase price
            down_payment: Down payment amount
            residual_value: Estimated residual value (if None, calculated from percentage)
            annual_interest_rate: Annual interest rate as decimal (e.g., 0.06 for 6%)
            term_months: Lease term in months
            residual_percentage: Residual value as percentage of price (if residual_value not provided)

        Returns:
            TRACLeaseCalculation with results and warnings
        """
        # Set defaults
        if annual_interest_rate is None:
            annual_interest_rate = self.typical_commercial_apr

        if residual_value is None:
            res_pct = residual_percentage or self.default_residual_percentage
            residual_value = vehicle_price * res_pct

        # Validate inputs
        warnings = []

        if vehicle_price <= 0:
            raise ValueError("Vehicle price must be positive")

        if down_payment < 0:
            raise ValueError("Down payment cannot be negative")

        if down_payment >= vehicle_price:
            raise ValueError("Down payment cannot exceed vehicle price")

        if residual_value < 0:
            raise ValueError("Residual value cannot be negative")

        if residual_value > vehicle_price:
            warnings.append(
                "⚠️ Residual value exceeds vehicle price - unusual for commercial vehicles"
            )

        if annual_interest_rate < 0 or annual_interest_rate > 0.25:
            warnings.append(
                f"⚠️ Interest rate {annual_interest_rate*100:.1f}% is outside normal range (3-15%)"
            )

        # Calculate adjusted capitalized cost
        C_adj = vehicle_price - down_payment

        # Calculate money factor
        # MF = APR / 2400
        # This converts APR to a monthly rate suitable for lease calculations
        MF = annual_interest_rate / 2400

        # Calculate monthly payment using TRAC formula
        # P_rent = (C_adj + R) × MF
        P_rent = (C_adj + residual_value) * MF

        # Calculate totals
        total_payments = P_rent * term_months
        total_cost = down_payment + total_payments

        # Calculate residual risk
        # This is the amount the lessee is exposed to if vehicle depreciates more than expected
        residual_risk = residual_value

        # Add TRAC-specific warnings
        warnings.append(
            "⚠️ IMPORTANT: TRAC lease is OPEN-ENDED - You bear the residual value risk"
        )
        warnings.append(
            f"⚠️ If vehicle value < ${residual_value:,.2f} at end of lease, you pay the difference"
        )
        warnings.append(
            f"⚠️ Maximum risk exposure: ${residual_risk:,.2f}"
        )

        if residual_value / vehicle_price > 0.5:
            warnings.append(
                "⚠️ High residual percentage (>50%) increases your risk significantly"
            )

        return TRACLeaseCalculation(
            vehicle_price=vehicle_price,
            down_payment=down_payment,
            residual_value=residual_value,
            annual_interest_rate=annual_interest_rate,
            term_months=term_months,
            adjusted_capitalized_cost=C_adj,
            money_factor=MF,
            monthly_payment=P_rent,
            total_payments=total_payments,
            residual_risk=residual_risk,
            warnings=warnings,
        )

    def format_result(self, result: TRACLeaseCalculation, language: str = "fr-CA") -> str:
        """Format calculation result for display.

        Args:
            result: TRACLeaseCalculation result
            language: Output language (fr-CA or en-US)

        Returns:
            Formatted string
        """
        if language == "fr-CA":
            output = "📊 CALCUL DE LOCATION TRAC\n\n"
            output += "Détails du véhicule:\n"
            output += f"  Prix du véhicule: {result.vehicle_price:,.2f} $\n"
            output += f"  Mise de fonds: {result.down_payment:,.2f} $\n"
            output += f"  Coût capitalisé ajusté: {result.adjusted_capitalized_cost:,.2f} $\n\n"

            output += "Conditions de location:\n"
            output += f"  Durée: {result.term_months} mois\n"
            output += f"  Taux d'intérêt annuel: {result.annual_interest_rate*100:.2f}%\n"
            output += f"  Facteur monétaire: {result.money_factor:.6f}\n"
            output += f"  Valeur résiduelle: {result.residual_value:,.2f} $\n\n"

            output += "💰 PAIEMENT MENSUEL: {:.2f} $\n\n".format(result.monthly_payment)

            output += "Résumé financier:\n"
            output += f"  Total des paiements: {result.total_payments:,.2f} $\n"
            output += f"  Coût total: {result.down_payment + result.total_payments:,.2f} $\n\n"

            output += "⚠️ AVERTISSEMENTS IMPORTANTS:\n"
            for warning in result.warnings:
                # Translate warnings
                warning_fr = warning.replace("IMPORTANT:", "IMPORTANT :")
                warning_fr = warning_fr.replace("OPEN-ENDED", "À DURÉE INDÉTERMINÉE")
                warning_fr = warning_fr.replace("You bear", "Vous assumez")
                warning_fr = warning_fr.replace("residual value risk", "le risque de valeur résiduelle")
                warning_fr = warning_fr.replace("If vehicle value", "Si la valeur du véhicule")
                warning_fr = warning_fr.replace("at end of lease, you pay the difference", "à la fin du bail, vous payez la différence")
                warning_fr = warning_fr.replace("Maximum risk exposure", "Exposition au risque maximale")
                warning_fr = warning_fr.replace("High residual percentage", "Pourcentage résiduel élevé")
                warning_fr = warning_fr.replace("increases your risk significantly", "augmente considérablement votre risque")

                output += f"  {warning_fr}\n"

            output += "\n🇨🇦 Conformité Loi 96: Le contrat final vous sera remis en français.\n"

        else:
            output = "📊 TRAC LEASE CALCULATION\n\n"
            output += "Vehicle Details:\n"
            output += f"  Vehicle price: ${result.vehicle_price:,.2f}\n"
            output += f"  Down payment: ${result.down_payment:,.2f}\n"
            output += f"  Adjusted capitalized cost: ${result.adjusted_capitalized_cost:,.2f}\n\n"

            output += "Lease Terms:\n"
            output += f"  Term: {result.term_months} months\n"
            output += f"  Annual interest rate: {result.annual_interest_rate*100:.2f}%\n"
            output += f"  Money factor: {result.money_factor:.6f}\n"
            output += f"  Residual value: ${result.residual_value:,.2f}\n\n"

            output += "💰 MONTHLY PAYMENT: ${:.2f}\n\n".format(result.monthly_payment)

            output += "Financial Summary:\n"
            output += f"  Total of payments: ${result.total_payments:,.2f}\n"
            output += f"  Total cost: ${result.down_payment + result.total_payments:,.2f}\n\n"

            output += "⚠️ IMPORTANT WARNINGS:\n"
            for warning in result.warnings:
                output += f"  {warning}\n"

            output += "\n🇨🇦 Bill 96 Compliance: Final contract will be provided in French.\n"

        return output

    def get_description(self) -> str:
        """Get tool description for agent framework."""
        return """Calculate TRAC (Terminal Rental Adjustment Clause) lease payments for commercial vehicles.

This tool calculates monthly lease payments using the formula:
P_rent = (C_adj + R) × MF

Where:
- C_adj = Adjusted capitalized cost (vehicle price - down payment)
- R = Residual value (estimated value at end of lease)
- MF = Money factor (APR / 2400)

IMPORTANT: TRAC leases are open-ended - the lessee bears residual value risk.

Inputs:
- vehicle_price: Vehicle purchase price
- down_payment: Down payment amount (default: $0)
- residual_value: Estimated residual value (default: 40% of price)
- annual_interest_rate: Annual interest rate (default: 6%)
- term_months: Lease term in months (default: 36)

Output: Monthly payment, total cost, and risk warnings"""


# Example usage
def main():
    """Example TRAC calculator usage."""
    calculator = CalculateTracLeaseTool()

    test_cases = [
        {
            "vehicle_price": 45000,
            "down_payment": 5000,
            "term_months": 36,
            "annual_interest_rate": 0.06,
            "residual_percentage": 0.40,
        },
        {
            "vehicle_price": 75000,
            "down_payment": 10000,
            "term_months": 48,
            "annual_interest_rate": 0.055,
            "residual_percentage": 0.35,
        },
    ]

    print("TRAC Lease Calculator - Testing\n")
    for i, case in enumerate(test_cases, 1):
        print(f"Test Case {i}:")
        result = calculator.calculate(**case)

        # English output
        print(calculator.format_result(result, language="en-US"))
        print("\n" + "="*80 + "\n")

        # French output
        print(calculator.format_result(result, language="fr-CA"))
        print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()

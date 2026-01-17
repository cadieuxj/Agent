"""Finance Manager Agent with TRAC lease calculation."""
from typing import Optional
from src.tools.trac_calculator import CalculateTracLeaseTool, TRACLeaseCalculation


class FinanceAgent:
    """Finance manager agent for lease and financing calculations.

    This agent:
    1. Handles financing inquiries
    2. Calculates TRAC lease payments
    3. Explains financing options
    4. Ensures Bill 96 compliance with French-first disclosures
    """

    def __init__(self):
        """Initialize finance agent."""
        self.trac_calculator = CalculateTracLeaseTool()

    async def calculate_trac_lease(
        self,
        vehicle_price: float,
        down_payment: float = 0.0,
        term_months: int = 36,
        annual_interest_rate: Optional[float] = None,
        residual_percentage: Optional[float] = None,
        language: str = "fr-CA",
    ) -> str:
        """Calculate TRAC lease payment and return formatted result.

        Args:
            vehicle_price: Vehicle price
            down_payment: Down payment amount
            term_months: Lease term in months
            annual_interest_rate: Annual interest rate (decimal)
            residual_percentage: Residual value percentage
            language: Output language

        Returns:
            Formatted calculation result
        """
        result = self.trac_calculator.calculate(
            vehicle_price=vehicle_price,
            down_payment=down_payment,
            term_months=term_months,
            annual_interest_rate=annual_interest_rate,
            residual_percentage=residual_percentage,
        )

        return self.trac_calculator.format_result(result, language)

    def get_financing_options(self, language: str = "fr-CA") -> str:
        """Get available financing options.

        Args:
            language: Output language

        Returns:
            Description of financing options
        """
        if language == "fr-CA":
            return """
🏦 OPTIONS DE FINANCEMENT DISPONIBLES

1. LOCATION TRAC (Terminal Rental Adjustment Clause)
   - Pour véhicules commerciaux à usage intensif
   - Paiements mensuels basés sur la valeur résiduelle
   - ⚠️ IMPORTANT: Vous assumez le risque de valeur résiduelle
   - Avantage: Paiements potentiellement plus bas
   - Désavantage: Risque financier à la fin du bail

2. FINANCEMENT TRADITIONNEL
   - Prêt commercial standard
   - Vous devenez propriétaire à la fin
   - Taux d'intérêt fixe ou variable
   - Pas de risque résiduel

3. LOCATION FERMÉE (Closed-End Lease)
   - Paiements fixes sans risque résiduel
   - Kilométrage limité
   - Retournez le véhicule à la fin
   - Idéal pour usage prévisible

🇨🇦 Conformité Loi 96:
Toutes les divulgations financières et le contrat final vous seront remis en français.

Voulez-vous que je calcule une soumission pour l'une de ces options?
"""
        else:
            return """
🏦 AVAILABLE FINANCING OPTIONS

1. TRAC LEASE (Terminal Rental Adjustment Clause)
   - For commercial vehicles with intensive use
   - Monthly payments based on residual value
   - ⚠️ IMPORTANT: You bear the residual value risk
   - Advantage: Potentially lower payments
   - Disadvantage: Financial risk at end of lease

2. TRADITIONAL FINANCING
   - Standard commercial loan
   - You own the vehicle at the end
   - Fixed or variable interest rate
   - No residual risk

3. CLOSED-END LEASE
   - Fixed payments with no residual risk
   - Limited mileage
   - Return vehicle at end
   - Ideal for predictable usage

🇨🇦 Bill 96 Compliance:
All financial disclosures and final contract will be provided in French.

Would you like me to calculate a quote for any of these options?
"""

    def get_trac_explanation(self, language: str = "fr-CA") -> str:
        """Get detailed TRAC lease explanation.

        Args:
            language: Output language

        Returns:
            TRAC lease explanation
        """
        if language == "fr-CA":
            return """
📚 QU'EST-CE QU'UNE LOCATION TRAC?

TRAC = Terminal Rental Adjustment Clause (Clause d'ajustement de location terminale)

Comment ça fonctionne:
1. Vous louez le véhicule commercial pour une période déterminée (ex: 36 mois)
2. Un paiement mensuel est calculé basé sur une valeur résiduelle estimée
3. À la fin du bail, le véhicule est évalué

Trois scénarios possibles à la fin:

✅ SCÉNARIO 1: Valeur réelle = Valeur résiduelle estimée
   → Vous ne payez rien de plus

⚠️ SCÉNARIO 2: Valeur réelle < Valeur résiduelle estimée
   → VOUS PAYEZ LA DIFFÉRENCE
   → Exemple: Estimé 20 000$, réel 15 000$ → Vous payez 5 000$

✅ SCÉNARIO 3: Valeur réelle > Valeur résiduelle estimée
   → VOUS RECEVEZ LA DIFFÉRENCE
   → Exemple: Estimé 20 000$, réel 25 000$ → Vous recevez 5 000$

Formule de calcul:
P_rent = (C_adj + R) × MF

Où:
- P_rent = Paiement mensuel
- C_adj = Coût capitalisé ajusté (prix - mise de fonds)
- R = Valeur résiduelle
- MF = Facteur monétaire (taux d'intérêt ÷ 2400)

⚠️ RISQUES IMPORTANTS:
- Usage intensif réduit la valeur → Vous payez plus
- Dommages au véhicule → Vous payez plus
- Marché défavorable → Vous payez plus
- C'est un bail "à durée indéterminée" (open-ended)

👍 AVANTAGES:
- Paiements mensuels généralement plus bas
- Flexibilité d'usage (pas de limite de kilométrage stricte)
- Potentiel de profit si le véhicule se déprécie moins que prévu

🇨🇦 Conformité Loi 96:
Le contrat final vous sera remis en français avec toutes les divulgations requises.
"""
        else:
            return """
📚 WHAT IS A TRAC LEASE?

TRAC = Terminal Rental Adjustment Clause

How it works:
1. You lease the commercial vehicle for a set period (e.g., 36 months)
2. Monthly payment is calculated based on an estimated residual value
3. At end of lease, the vehicle is appraised

Three possible scenarios at the end:

✅ SCENARIO 1: Actual value = Estimated residual value
   → You pay nothing additional

⚠️ SCENARIO 2: Actual value < Estimated residual value
   → YOU PAY THE DIFFERENCE
   → Example: Estimated $20,000, actual $15,000 → You pay $5,000

✅ SCENARIO 3: Actual value > Estimated residual value
   → YOU RECEIVE THE DIFFERENCE
   → Example: Estimated $20,000, actual $25,000 → You receive $5,000

Calculation formula:
P_rent = (C_adj + R) × MF

Where:
- P_rent = Monthly payment
- C_adj = Adjusted capitalized cost (price - down payment)
- R = Residual value
- MF = Money factor (interest rate ÷ 2400)

⚠️ IMPORTANT RISKS:
- Heavy use reduces value → You pay more
- Vehicle damage → You pay more
- Unfavorable market → You pay more
- This is an "open-ended" lease

👍 ADVANTAGES:
- Generally lower monthly payments
- Usage flexibility (no strict mileage limits)
- Profit potential if vehicle depreciates less than expected

🇨🇦 Bill 96 Compliance:
Final contract will be provided in French with all required disclosures.
"""


# Example usage
async def main():
    """Example finance agent usage."""
    agent = FinanceAgent()

    print("Finance Agent - TRAC Lease Calculator\n")
    print("="*80 + "\n")

    # Get financing options
    print(agent.get_financing_options(language="fr-CA"))
    print("\n" + "="*80 + "\n")

    # Get TRAC explanation
    print(agent.get_trac_explanation(language="fr-CA"))
    print("\n" + "="*80 + "\n")

    # Calculate example lease
    print("Example Calculation:\n")
    result = await agent.calculate_trac_lease(
        vehicle_price=50000,
        down_payment=5000,
        term_months=36,
        annual_interest_rate=0.06,
        residual_percentage=0.40,
        language="fr-CA",
    )
    print(result)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

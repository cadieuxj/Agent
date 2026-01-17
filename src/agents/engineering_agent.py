"""Engineering Expert Agent with vector store integration."""
import sys
from pathlib import Path
from typing import List, Dict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data.rag_pipeline import RAGPipeline


class EngineeringAgent:
    """Engineering expert agent for technical questions about upfits, PTO, and GVWR.

    This agent:
    1. Answers technical questions about vehicle modifications
    2. Provides PTO (Power Take-Off) specifications
    3. Calculates GVWR compliance for upfits
    4. References Body Builder guides via RAG pipeline
    """

    def __init__(self, rag_pipeline: RAGPipeline):
        """Initialize engineering agent.

        Args:
            rag_pipeline: RAG pipeline for document search
        """
        self.rag = rag_pipeline

    async def answer_technical_question(
        self,
        question: str,
        language: str = "fr-CA",
        top_k: int = 3,
    ) -> str:
        """Answer technical question using RAG pipeline.

        Args:
            question: Technical question
            language: Response language
            top_k: Number of document chunks to retrieve

        Returns:
            Answer with references
        """
        # Search relevant documents
        results = await self.rag.search(question, top_k=top_k)

        if not results:
            if language == "fr-CA":
                return """Je n'ai pas trouvé d'information spécifique dans les guides Body Builder.
Pourriez-vous reformuler votre question ou me donner plus de détails?"""
            else:
                return """I couldn't find specific information in the Body Builder guides.
Could you rephrase your question or provide more details?"""

        # Build answer from results
        if language == "fr-CA":
            response = "📋 INFORMATION TECHNIQUE\n\n"
            response += "Basé sur les guides Body Builder, voici ce que j'ai trouvé:\n\n"

            for i, result in enumerate(results, 1):
                response += f"--- Référence {i} ---\n"
                response += f"{result['content']}\n"
                response += f"(Source: {Path(result['source_file']).name}, Page {result['page_number']})\n\n"

            response += "💡 RECOMMANDATIONS:\n"
            response += "- Consultez toujours un ingénieur certifié avant toute modification\n"
            response += "- Vérifiez la conformité PNBV (Poids Nominal Brut du Véhicule)\n"
            response += "- Assurez-vous que toutes les modifications respectent les normes Transport Canada\n\n"

            response += "Avez-vous besoin de précisions supplémentaires?"

        else:
            response = "📋 TECHNICAL INFORMATION\n\n"
            response += "Based on the Body Builder guides, here's what I found:\n\n"

            for i, result in enumerate(results, 1):
                response += f"--- Reference {i} ---\n"
                response += f"{result['content']}\n"
                response += f"(Source: {Path(result['source_file']).name}, Page {result['page_number']})\n\n"

            response += "💡 RECOMMENDATIONS:\n"
            response += "- Always consult a certified engineer before any modifications\n"
            response += "- Verify GVWR (Gross Vehicle Weight Rating) compliance\n"
            response += "- Ensure all modifications meet Transport Canada standards\n\n"

            response += "Do you need any additional clarification?"

        return response

    def calculate_available_payload(
        self,
        gvwr: float,
        curb_weight: float,
        num_passengers: int = 2,
        passenger_weight: float = 150.0,
        language: str = "fr-CA",
    ) -> str:
        """Calculate available payload for upfitting.

        Args:
            gvwr: Gross Vehicle Weight Rating (lbs)
            curb_weight: Vehicle curb weight (lbs)
            num_passengers: Number of passengers
            passenger_weight: Weight per passenger (lbs)
            language: Response language

        Returns:
            Formatted calculation result
        """
        # Calculate available capacity
        occupant_weight = num_passengers * passenger_weight
        available_capacity = gvwr - curb_weight - occupant_weight

        if language == "fr-CA":
            output = "⚖️ CALCUL DE CHARGE UTILE DISPONIBLE\n\n"
            output += "Spécifications du véhicule:\n"
            output += f"  PNBV (Poids Nominal Brut du Véhicule): {gvwr:,.0f} lb\n"
            output += f"  Poids à vide: {curb_weight:,.0f} lb\n"
            output += f"  Passagers ({num_passengers} × {passenger_weight:.0f} lb): {occupant_weight:,.0f} lb\n\n"

            output += f"💰 CAPACITÉ DISPONIBLE: {available_capacity:,.0f} lb\n\n"

            output += "Cette capacité doit couvrir:\n"
            output += "  • Poids de l'équipement ajouté (modification)\n"
            output += "  • Charge utile (cargo, outils, etc.)\n\n"

            if available_capacity < 1000:
                output += "⚠️ AVERTISSEMENT: Capacité limitée. Modifications lourdes non recommandées.\n\n"
            elif available_capacity > 5000:
                output += "✅ Bonne capacité pour modifications substantielles.\n\n"

            output += "Exemples de poids de modifications typiques:\n"
            output += "  • Corps de service (acier): 1 200 - 1 800 lb\n"
            output += "  • Corps de service (aluminium): 800 - 1 200 lb\n"
            output += "  • Benne basculante: 1 500 - 2 500 lb\n"
            output += "  • Petite grue: 800 - 1 500 lb\n"

        else:
            output = "⚖️ AVAILABLE PAYLOAD CALCULATION\n\n"
            output += "Vehicle Specifications:\n"
            output += f"  GVWR (Gross Vehicle Weight Rating): {gvwr:,.0f} lb\n"
            output += f"  Curb Weight: {curb_weight:,.0f} lb\n"
            output += f"  Passengers ({num_passengers} × {passenger_weight:.0f} lb): {occupant_weight:,.0f} lb\n\n"

            output += f"💰 AVAILABLE CAPACITY: {available_capacity:,.0f} lb\n\n"

            output += "This capacity must cover:\n"
            output += "  • Weight of added equipment (upfit)\n"
            output += "  • Payload (cargo, tools, etc.)\n\n"

            if available_capacity < 1000:
                output += "⚠️ WARNING: Limited capacity. Heavy upfits not recommended.\n\n"
            elif available_capacity > 5000:
                output += "✅ Good capacity for substantial modifications.\n\n"

            output += "Typical Upfit Weight Examples:\n"
            output += "  • Service Body (steel): 1,200 - 1,800 lb\n"
            output += "  • Service Body (aluminum): 800 - 1,200 lb\n"
            output += "  • Dump Body: 1,500 - 2,500 lb\n"
            output += "  • Small Crane: 800 - 1,500 lb\n"

        return output

    def get_pto_specifications(self, pto_type: str = "all", language: str = "fr-CA") -> str:
        """Get PTO (Power Take-Off) specifications.

        Args:
            pto_type: Type of PTO (engine, transmission, split-shaft, or all)
            language: Response language

        Returns:
            PTO specifications
        """
        pto_data = {
            "engine": {
                "name_fr": "PTO entraîné par moteur",
                "name_en": "Engine-Driven PTO",
                "max_torque": "500 lb-ft",
                "operating_speed": "1000-2100 RPM",
                "applications_fr": "Pompes hydrauliques, compresseurs",
                "applications_en": "Hydraulic pumps, compressors",
            },
            "transmission": {
                "name_fr": "PTO de transmission",
                "name_en": "Transmission PTO",
                "max_torque": "300 lb-ft",
                "operating_speed": "600-1800 RPM",
                "applications_fr": "Bennes basculantes, équipement auxiliaire",
                "applications_en": "Dump bodies, auxiliary equipment",
            },
            "split-shaft": {
                "name_fr": "PTO à arbre divisé",
                "name_en": "Split-Shaft PTO",
                "max_torque": "400 lb-ft",
                "operating_speed": "800-2000 RPM",
                "applications_fr": "Malaxeurs à béton, grues",
                "applications_en": "Concrete mixers, crane operations",
            },
        }

        if language == "fr-CA":
            output = "⚙️ SPÉCIFICATIONS PTO (PRISE DE FORCE)\n\n"

            types_to_show = [pto_type] if pto_type != "all" else pto_data.keys()

            for pto_key in types_to_show:
                if pto_key in pto_data:
                    pto = pto_data[pto_key]
                    output += f"🔧 {pto['name_fr']}\n"
                    output += f"   Couple maximal: {pto['max_torque']}\n"
                    output += f"   Vitesse de fonctionnement: {pto['operating_speed']}\n"
                    output += f"   Applications: {pto['applications_fr']}\n\n"

            output += "⚠️ IMPORTANT:\n"
            output += "• Toutes les installations PTO doivent maintenir un dégagement minimal\n"
            output += "  de 12 pouces des systèmes d'échappement\n"
            output += "• Installation par un technicien certifié requise\n"
            output += "• Vérifiez la compatibilité avec le modèle spécifique du véhicule\n"

        else:
            output = "⚙️ PTO (POWER TAKE-OFF) SPECIFICATIONS\n\n"

            types_to_show = [pto_type] if pto_type != "all" else pto_data.keys()

            for pto_key in types_to_show:
                if pto_key in pto_data:
                    pto = pto_data[pto_key]
                    output += f"🔧 {pto['name_en']}\n"
                    output += f"   Max Torque: {pto['max_torque']}\n"
                    output += f"   Operating Speed: {pto['operating_speed']}\n"
                    output += f"   Applications: {pto['applications_en']}\n\n"

            output += "⚠️ IMPORTANT:\n"
            output += "• All PTO installations must maintain minimum 12\" clearance\n"
            output += "  from exhaust systems\n"
            output += "• Installation by certified technician required\n"
            output += "• Verify compatibility with specific vehicle model\n"

        return output


# Example usage
async def main():
    """Example engineering agent usage."""
    # Initialize RAG pipeline
    rag = RAGPipeline(use_mock=True)

    # Ingest mock documents
    await rag.ingest_documents(["./data/pdfs/body_builder_guide.pdf"])

    # Initialize agent
    agent = EngineeringAgent(rag_pipeline=rag)

    print("Engineering Agent - Testing\n")
    print("="*80 + "\n")

    # Test 1: Technical question
    question = "What are the PTO specifications for hydraulic pumps?"
    print(f"Question: {question}\n")
    answer = await agent.answer_technical_question(question, language="en-US")
    print(answer)
    print("\n" + "="*80 + "\n")

    # Test 2: Payload calculation
    print("Payload Calculation:\n")
    payload_result = agent.calculate_available_payload(
        gvwr=14000,
        curb_weight=8500,
        num_passengers=2,
        language="en-US",
    )
    print(payload_result)
    print("\n" + "="*80 + "\n")

    # Test 3: PTO specifications
    print("PTO Specifications:\n")
    pto_specs = agent.get_pto_specifications(pto_type="all", language="en-US")
    print(pto_specs)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

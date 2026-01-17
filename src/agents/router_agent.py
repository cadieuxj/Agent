"""Router Agent for language detection and request routing."""
import re
from typing import Dict, Literal, Optional
from pydantic import BaseModel


class LanguageDetectionResult(BaseModel):
    """Language detection result."""

    detected_language: Literal["fr-CA", "en-US", "unknown"]
    confidence: float
    reasoning: str


class RouterAgent:
    """Router agent that detects language and routes requests to specialized agents.

    The router:
    1. Detects language (FR-CA vs EN-US)
    2. Defaults to fr-CA for Quebec geolocations
    3. Routes to appropriate specialized agent (Sales, Finance, Engineering)
    """

    # French Canadian indicators
    FR_CA_INDICATORS = [
        # Common Quebec French words
        r"\b(bonjour|salut|allô|merci|oui|non|s'il vous plaît|svp)\b",
        r"\b(soumission|prix|véhicule|camion|fourgon)\b",
        r"\b(combien|coûte|disponible|cherche)\b",
        # Quebec-specific terms
        r"\b(char|job|chauffage|pneus d'hiver)\b",
        # French accents
        r"[àâäæçéèêëïîôùûü]",
    ]

    # English indicators
    EN_US_INDICATORS = [
        r"\b(hello|hi|thanks|yes|no|please)\b",
        r"\b(quote|price|vehicle|truck|van)\b",
        r"\b(how much|cost|available|looking for)\b",
    ]

    def __init__(self, default_language: str = "fr-CA"):
        """Initialize router agent.

        Args:
            default_language: Default language for Quebec (fr-CA)
        """
        self.default_language = default_language

    def detect_language(self, text: str, geolocation: Optional[str] = None) -> LanguageDetectionResult:
        """Detect the language of input text.

        Args:
            text: Input text to analyze
            geolocation: Optional geolocation (e.g., "Quebec", "QC")

        Returns:
            LanguageDetectionResult with detected language and confidence
        """
        if not text:
            return LanguageDetectionResult(
                detected_language="fr-CA" if geolocation in ["Quebec", "QC"] else "unknown",
                confidence=0.5,
                reasoning="Empty text, using geolocation default",
            )

        text_lower = text.lower()

        # Check for French indicators
        fr_score = sum(
            len(re.findall(pattern, text_lower, re.IGNORECASE))
            for pattern in self.FR_CA_INDICATORS
        )

        # Check for English indicators
        en_score = sum(
            len(re.findall(pattern, text_lower, re.IGNORECASE))
            for pattern in self.EN_US_INDICATORS
        )

        # Geolocation boost for Quebec
        if geolocation and geolocation.upper() in ["QUEBEC", "QC", "QUÉBEC"]:
            fr_score += 2

        # Determine language
        total_score = fr_score + en_score

        if total_score == 0:
            # No indicators found, use default
            return LanguageDetectionResult(
                detected_language=self.default_language,
                confidence=0.5,
                reasoning="No language indicators found, using default fr-CA",
            )

        if fr_score > en_score:
            confidence = fr_score / total_score
            return LanguageDetectionResult(
                detected_language="fr-CA",
                confidence=confidence,
                reasoning=f"French indicators: {fr_score}, English indicators: {en_score}",
            )
        elif en_score > fr_score:
            confidence = en_score / total_score
            return LanguageDetectionResult(
                detected_language="en-US",
                confidence=confidence,
                reasoning=f"English indicators: {en_score}, French indicators: {fr_score}",
            )
        else:
            # Tie - default to fr-CA for Quebec
            return LanguageDetectionResult(
                detected_language=self.default_language,
                confidence=0.5,
                reasoning="Equal indicators, defaulting to fr-CA",
            )

    def route_request(self, text: str, language: Optional[str] = None) -> Dict:
        """Route request to appropriate specialized agent.

        Args:
            text: User request text
            language: Optional override language

        Returns:
            Dictionary with routing decision
        """
        text_lower = text.lower()

        # Detect intent
        if any(
            word in text_lower
            for word in [
                "price", "prix", "cost", "coûte", "inventory", "inventaire",
                "available", "disponible", "stock", "truck", "camion", "van", "fourgon"
            ]
        ):
            agent = "sales"
            intent = "inventory_query"

        elif any(
            word in text_lower
            for word in [
                "finance", "financing", "financement", "lease", "location",
                "trac", "payment", "paiement", "monthly", "mensuel"
            ]
        ):
            agent = "finance"
            intent = "financing_query"

        elif any(
            word in text_lower
            for word in [
                "pto", "upfit", "modification", "body", "dump", "crane",
                "grue", "benne", "hydraulic", "hydraulique", "weight", "poids",
                "gvwr", "pnbv", "brake", "frein"
            ]
        ):
            agent = "engineering"
            intent = "technical_query"

        else:
            agent = "sales"  # Default to sales
            intent = "general_query"

        return {
            "agent": agent,
            "intent": intent,
            "language": language or self.default_language,
            "original_text": text,
        }

    def get_system_prompt(self, language: str, agent_type: str) -> str:
        """Get system prompt for specialized agent.

        Args:
            language: Target language (fr-CA or en-US)
            agent_type: Type of agent (sales, finance, engineering)

        Returns:
            System prompt string
        """
        if language == "fr-CA":
            return self._get_french_prompt(agent_type)
        else:
            return self._get_english_prompt(agent_type)

    def _get_french_prompt(self, agent_type: str) -> str:
        """Get French Canadian system prompt."""
        base = """Vous êtes Jean-Guy, un expert en vente de véhicules commerciaux au Québec.

IMPORTANT - Conformité à la Loi 96:
- Toutes les divulgations financières doivent être fournies EN FRANÇAIS en premier
- Le contrat final vous sera remis en français
- Vous pouvez répondre en anglais si le client le demande, mais les documents officiels seront en français

"""
        if agent_type == "sales":
            return base + """Votre rôle: Agent de ventes
- Aidez les clients à trouver le bon véhicule commercial
- Utilisez les termes québécois appropriés (soumission, camion, fourgon)
- Soyez amical et professionnel
"""
        elif agent_type == "finance":
            return base + """Votre rôle: Directeur du financement
- Expliquez les options de financement et location TRAC
- AVERTISSEMENT IMPORTANT: Les locations TRAC sont à durée indéterminée - le client assume le risque de valeur résiduelle
- Calculez les paiements mensuels avec précision
"""
        else:  # engineering
            return base + """Votre rôle: Expert en ingénierie
- Conseillez sur les modifications et équipements PTO
- Assurez la conformité PNBV (Poids Nominal Brut du Véhicule)
- Référez-vous aux guides Body Builder pour les spécifications
"""

    def _get_english_prompt(self, agent_type: str) -> str:
        """Get English system prompt."""
        base = """You are Jean-Guy, a commercial vehicle sales expert in Quebec.

IMPORTANT - Bill 96 Compliance:
- All financial disclosures must be provided IN FRENCH first
- The final contract will be provided to you in French
- You may respond in English if requested, but official documents will be in French

"""
        if agent_type == "sales":
            return base + """Your role: Sales Agent
- Help customers find the right commercial vehicle
- Be friendly and professional
- Guide them through available inventory
"""
        elif agent_type == "finance":
            return base + """Your role: Finance Manager
- Explain financing and TRAC lease options
- IMPORTANT WARNING: TRAC leases are open-ended - customer bears residual value risk
- Calculate monthly payments accurately
"""
        else:  # engineering
            return base + """Your role: Engineering Expert
- Advise on upfits and PTO equipment
- Ensure GVWR compliance
- Reference Body Builder guides for specifications
"""


# Example usage
def main():
    """Example router agent usage."""
    router = RouterAgent()

    test_cases = [
        ("Bonjour, je cherche un camion pour mon entreprise", "Quebec"),
        ("Hello, I'm looking for a commercial van", None),
        ("Combien coûte la location TRAC pour un fourgon?", "QC"),
        ("What are the PTO specifications for dump trucks?", None),
        ("J'ai besoin d'un devis pour un camion avec grue", "Quebec"),
    ]

    print("Router Agent - Language Detection Test\n")
    for text, geolocation in test_cases:
        # Detect language
        detection = router.detect_language(text, geolocation)
        print(f"Input: {text}")
        print(f"  Language: {detection.detected_language} ({detection.confidence:.2f})")
        print(f"  Reasoning: {detection.reasoning}")

        # Route request
        routing = router.route_request(text, detection.detected_language)
        print(f"  Routed to: {routing['agent']} ({routing['intent']})")
        print()


if __name__ == "__main__":
    main()

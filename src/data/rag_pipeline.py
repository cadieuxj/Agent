"""RAG Pipeline for Body Builder Guides using Azure AI Document Intelligence."""
import json
import pickle
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import numpy as np


@dataclass
class DocumentChunk:
    """Represents a chunk of document text with metadata."""

    content: str
    page_number: int
    chunk_id: str
    source_file: str
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class MockVectorStore:
    """Mock vector store for local development."""

    def __init__(self, store_path: str = "./data/vector_store/embeddings.pkl"):
        """Initialize mock vector store.

        Args:
            store_path: Path to save/load embeddings
        """
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.chunks: List[DocumentChunk] = []
        self.embeddings: List[np.ndarray] = []

    def add_chunks(self, chunks: List[DocumentChunk], embeddings: List[np.ndarray]):
        """Add document chunks with their embeddings."""
        self.chunks.extend(chunks)
        self.embeddings.extend(embeddings)

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Tuple[DocumentChunk, float]]:
        """Search for similar chunks using cosine similarity.

        Args:
            query_embedding: Query vector
            top_k: Number of results to return

        Returns:
            List of (chunk, score) tuples
        """
        if not self.embeddings:
            return []

        # Calculate cosine similarity
        scores = []
        for emb in self.embeddings:
            similarity = np.dot(query_embedding, emb) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(emb)
            )
            scores.append(similarity)

        # Get top-k indices
        top_indices = np.argsort(scores)[-top_k:][::-1]

        results = [(self.chunks[i], float(scores[i])) for i in top_indices]
        return results

    def save(self):
        """Save vector store to disk."""
        data = {
            "chunks": self.chunks,
            "embeddings": self.embeddings,
        }
        with open(self.store_path, "wb") as f:
            pickle.dump(data, f)

    def load(self):
        """Load vector store from disk."""
        if self.store_path.exists():
            with open(self.store_path, "rb") as f:
                data = pickle.load(f)
                self.chunks = data["chunks"]
                self.embeddings = data["embeddings"]


class DocumentProcessor:
    """Process PDF documents using Azure AI Document Intelligence."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        use_mock: bool = True,
    ):
        """Initialize document processor.

        Args:
            endpoint: Azure Document Intelligence endpoint
            api_key: Azure Document Intelligence API key
            use_mock: Use mock processing for local development
        """
        self.endpoint = endpoint
        self.api_key = api_key
        self.use_mock = use_mock

        if not use_mock and endpoint and api_key:
            from azure.ai.formrecognizer import DocumentAnalysisClient
            from azure.core.credentials import AzureKeyCredential

            self.client = DocumentAnalysisClient(
                endpoint=endpoint, credential=AzureKeyCredential(api_key)
            )
        else:
            self.client = None

    async def process_pdf(self, pdf_path: str) -> List[DocumentChunk]:
        """Process a PDF file and extract text chunks.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of DocumentChunk objects
        """
        if self.use_mock or not self.client:
            return self._mock_process_pdf(pdf_path)

        # Real Azure Document Intelligence processing
        with open(pdf_path, "rb") as f:
            poller = self.client.begin_analyze_document("prebuilt-layout", document=f)
            result = poller.result()

        chunks = []
        for page_num, page in enumerate(result.pages, start=1):
            # Extract tables
            for table in getattr(result, "tables", []):
                if table.bounding_regions[0].page_number == page_num:
                    table_md = self._table_to_markdown(table)
                    chunk = DocumentChunk(
                        content=table_md,
                        page_number=page_num,
                        chunk_id=f"{Path(pdf_path).stem}_p{page_num}_table",
                        source_file=pdf_path,
                        metadata={"type": "table"},
                    )
                    chunks.append(chunk)

            # Extract paragraphs
            for para_idx, paragraph in enumerate(
                getattr(page, "lines", []) if hasattr(page, "lines") else []
            ):
                chunk = DocumentChunk(
                    content=paragraph.content,
                    page_number=page_num,
                    chunk_id=f"{Path(pdf_path).stem}_p{page_num}_para{para_idx}",
                    source_file=pdf_path,
                    metadata={"type": "paragraph"},
                )
                chunks.append(chunk)

        return chunks

    def _mock_process_pdf(self, pdf_path: str) -> List[DocumentChunk]:
        """Mock PDF processing for local development."""
        # Simulate Body Builder Guide content
        mock_content = {
            1: """
# Body Builder Guide - Commercial Vehicles

## Power Take-Off (PTO) Specifications

| PTO Type | Max Torque | Operating Speed | Application |
|----------|------------|-----------------|-------------|
| Engine-Driven PTO | 500 lb-ft | 1000-2100 RPM | Hydraulic pumps, compressors |
| Transmission PTO | 300 lb-ft | 600-1800 RPM | Dump bodies, auxiliary equipment |
| Split-Shaft PTO | 400 lb-ft | 800-2000 RPM | Concrete mixers, crane operations |

**Important**: All PTO installations must maintain minimum 12" clearance from exhaust systems.
""",
            2: """
## Upfit Weight Calculations

### GVWR Compliance

To determine available payload for upfitting:

1. Start with vehicle GVWR (Gross Vehicle Weight Rating)
2. Subtract base curb weight
3. Subtract estimated occupant weight (150 lbs per seat)
4. Remaining capacity = Maximum upfit weight + payload

**Example for Class 4 Truck (14,000 lbs GVWR)**:
- Base curb weight: 8,500 lbs
- Occupant weight (2 seats): 300 lbs
- Available capacity: 5,200 lbs

### Common Upfit Weights

| Upfit Type | Typical Weight | Notes |
|------------|----------------|-------|
| Service Body | 1,200-1,800 lbs | Steel construction |
| Aluminum Service Body | 800-1,200 lbs | Lighter option |
| Dump Body | 1,500-2,500 lbs | Varies by size |
| Crane (Small) | 800-1,500 lbs | Plus boom weight |
""",
            3: """
## Brake System Requirements

### Air Brake Upfits

When installing auxiliary air systems:
- Minimum compressor capacity: 12 CFM
- Air tank capacity: 30 gallons minimum
- Pressure switch setting: 120-140 PSI

### Hydraulic Brake Considerations

For trailers and auxiliary braking:
- Brake controller rating must match GVWR
- Wiring must be 10 AWG minimum
- Breakaway system required for trailers >3,000 lbs
""",
        }

        chunks = []
        for page_num, content in mock_content.items():
            chunk = DocumentChunk(
                content=content.strip(),
                page_number=page_num,
                chunk_id=f"{Path(pdf_path).stem}_p{page_num}",
                source_file=pdf_path,
                metadata={"type": "mock", "source": "body_builder_guide"},
            )
            chunks.append(chunk)

        return chunks

    def _table_to_markdown(self, table) -> str:
        """Convert Azure Document Intelligence table to Markdown."""
        if not table.cells:
            return ""

        # Determine table dimensions
        max_row = max(cell.row_index for cell in table.cells)
        max_col = max(cell.column_index for cell in table.cells)

        # Create table grid
        grid = [[None for _ in range(max_col + 1)] for _ in range(max_row + 1)]

        for cell in table.cells:
            grid[cell.row_index][cell.column_index] = cell.content

        # Convert to markdown
        md_lines = []
        for row_idx, row in enumerate(grid):
            md_lines.append("| " + " | ".join(cell or "" for cell in row) + " |")
            if row_idx == 0:  # Add header separator
                md_lines.append("| " + " | ".join("---" for _ in row) + " |")

        return "\n".join(md_lines)


class RAGPipeline:
    """Complete RAG pipeline for Body Builder guides."""

    def __init__(
        self,
        document_intelligence_endpoint: Optional[str] = None,
        document_intelligence_key: Optional[str] = None,
        vector_store_path: str = "./data/vector_store/embeddings.pkl",
        use_mock: bool = True,
    ):
        """Initialize RAG pipeline.

        Args:
            document_intelligence_endpoint: Azure DI endpoint
            document_intelligence_key: Azure DI API key
            vector_store_path: Path to vector store
            use_mock: Use mock services for local development
        """
        self.processor = DocumentProcessor(
            endpoint=document_intelligence_endpoint,
            api_key=document_intelligence_key,
            use_mock=use_mock,
        )
        self.vector_store = MockVectorStore(store_path=vector_store_path)
        self.use_mock = use_mock

    async def ingest_documents(self, pdf_paths: List[str]):
        """Ingest PDF documents into the vector store.

        Args:
            pdf_paths: List of paths to PDF files
        """
        all_chunks = []

        for pdf_path in pdf_paths:
            print(f"Processing: {pdf_path}")
            chunks = await self.processor.process_pdf(pdf_path)
            all_chunks.extend(chunks)
            print(f"  Extracted {len(chunks)} chunks")

        # Generate mock embeddings (in production, use Azure OpenAI embeddings)
        embeddings = self._generate_mock_embeddings(all_chunks)

        self.vector_store.add_chunks(all_chunks, embeddings)
        self.vector_store.save()

        print(f"\nTotal chunks indexed: {len(all_chunks)}")

    def _generate_mock_embeddings(self, chunks: List[DocumentChunk]) -> List[np.ndarray]:
        """Generate mock embeddings for testing."""
        # In production, replace with Azure OpenAI embeddings API
        embeddings = []
        for chunk in chunks:
            # Simple hash-based embedding for testing
            embedding = np.random.RandomState(hash(chunk.content) % (2**32)).randn(1536)
            embedding = embedding / np.linalg.norm(embedding)
            embeddings.append(embedding)
        return embeddings

    async def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for relevant document chunks.

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            List of relevant chunks with scores
        """
        # Load vector store
        self.vector_store.load()

        # Generate query embedding
        query_embedding = self._generate_mock_embeddings(
            [DocumentChunk(content=query, page_number=0, chunk_id="query", source_file="")]
        )[0]

        # Search
        results = self.vector_store.search(query_embedding, top_k)

        # Format results
        formatted_results = []
        for chunk, score in results:
            formatted_results.append(
                {
                    "content": chunk.content,
                    "page_number": chunk.page_number,
                    "source_file": chunk.source_file,
                    "score": score,
                    "metadata": chunk.metadata,
                }
            )

        return formatted_results


# Example usage
async def main():
    """Example RAG pipeline usage."""
    rag = RAGPipeline(use_mock=True)

    # Ingest documents
    pdf_files = ["./data/pdfs/body_builder_guide.pdf"]
    await rag.ingest_documents(pdf_files)

    # Search
    query = "What are the PTO specifications for hydraulic pumps?"
    results = await rag.search(query, top_k=3)

    print(f"\nSearch results for: '{query}'\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. Score: {result['score']:.3f}")
        print(f"   Source: {result['source_file']} (Page {result['page_number']})")
        print(f"   Content: {result['content'][:200]}...")
        print()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

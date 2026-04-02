"""
============================================================
SemantiCite.ai — Mock Data for Semantic Scholar API
============================================================
PURPOSE:
    Provides realistic fake data for local development while
    waiting for Semantic Scholar API key approval or avoiding
    rate limits.

THEME:
    The "Attention Mechanism" and Transformer genealogy.
============================================================
"""

from db.models import PaperNode, CitationContext

# === Mock Papers ===
MOCK_PAPERS = {
    "paper_1": PaperNode(
        paper_id="paper_1_attention_is_all_you_need",
        title="Attention Is All You Need",
        authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit", "Llion Jones", "Aidan N. Gomez", "Lukasz Kaiser", "Illia Polosukhin"],
        year=2017,
        abstract="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
        citation_count=101500,
        url="https://arxiv.org/abs/1706.03762",
        venue="NeurIPS",
        fields_of_study=["Computer Science"]
    ),
    "paper_2": PaperNode(
        paper_id="paper_2_bert",
        title="BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        authors=["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"],
        year=2018,
        abstract="We introduce a new language representation model called BERT...",
        citation_count=85000,
        url="https://arxiv.org/abs/1810.04805",
        venue="NAACL",
        fields_of_study=["Computer Science"]
    ),
    "paper_3": PaperNode(
        paper_id="paper_3_seq2seq",
        title="Sequence to Sequence Learning with Neural Networks",
        authors=["Ilya Sutskever", "Oriol Vinyals", "Quoc V. Le"],
        year=2014,
        abstract="Deep Neural Networks (DNNs) are powerful models that have achieved excellent performance...",
        citation_count=23000,
        url="https://arxiv.org/abs/1409.3215",
        venue="NeurIPS",
        fields_of_study=["Computer Science"]
    ),
    "paper_4": PaperNode(
        paper_id="paper_4_linformer",
        title="Linformer: Self-Attention with Linear Complexity",
        authors=["Sinong Wang", "Belinda Z. Li", "Madian Khabsa", "Hao Fang", "Hao Ma"],
        year=2020,
        abstract="Large transformer models have achieved extraordinary success... However, training them requires significant resources...",
        citation_count=1500,
        url="https://arxiv.org/abs/2006.04768",
        venue="arXiv",
        fields_of_study=["Computer Science"]
    )
}

# === Mock Responses ===
# Simulating search response
MOCK_SEARCH_RESULTS = [MOCK_PAPERS["paper_1"], MOCK_PAPERS["paper_2"]]

# Simulating references (Paper 1 cites Paper 3)
MOCK_REFERENCES = {
    "paper_1_attention_is_all_you_need": [
        {
            "paper": MOCK_PAPERS["paper_3"],
            "contexts": [
                CitationContext(
                    citing_paper_id="paper_1_attention_is_all_you_need",
                    cited_paper_id="paper_3_seq2seq",
                    context_text="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder [Sutskever et al., 2014].",
                    intents=["Background"]
                ),
                CitationContext(
                    citing_paper_id="paper_1_attention_is_all_you_need",
                    cited_paper_id="paper_3_seq2seq",
                    context_text="However, our approach replaces the recurrent layers used by [Sutskever et al., 2014] with entirely self-attention mechanisms.",
                    intents=["Method"]
                )
            ],
            "is_influential": True
        }
    ]
}

# Simulating citations (Papers 2 and 4 cite Paper 1)
MOCK_CITATIONS = {
    "paper_1_attention_is_all_you_need": [
        {
            "paper": MOCK_PAPERS["paper_2"],
            "contexts": [
                CitationContext(
                    citing_paper_id="paper_2_bert",
                    cited_paper_id="paper_1_attention_is_all_you_need",
                    context_text="Building upon the original Transformer architecture proposed by Vaswani et al. (2017), we introduce a bidirectional approach.",
                    intents=["Background"]
                )
            ],
            "is_influential": True
        },
        {
            "paper": MOCK_PAPERS["paper_4"],
            "contexts": [
                CitationContext(
                    citing_paper_id="paper_4_linformer",
                    cited_paper_id="paper_1_attention_is_all_you_need",
                    context_text="While the Transformer (Vaswani et al., 2017) is powerful, its self-attention mechanism suffers from O(N^2) time and space complexity. Our method directly addresses this limitation.",
                    intents=["Background", "Method"]
                )
            ],
            "is_influential": True
        }
    ]
}

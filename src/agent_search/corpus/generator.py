"""Generate deterministic, synthetic retrieval fixtures for local development."""

import argparse
import json
from collections.abc import Iterable
from pathlib import Path

from agent_search.corpus.schemas import CorpusDocument, Domain, RelevanceJudgment, SearchQuery

DEFAULT_OUTPUT_DIRECTORY = Path("data/synthetic")


def build_documents() -> list[CorpusDocument]:
    """Return a small, intentionally fictional bilingual document corpus."""

    return [
        CorpusDocument(
            document_id="news-han-river-transit",
            domain=Domain.NEWS,
            language="en",
            title="Han River Metro adds late-evening trains",
            body=(
                "The fictional Han River Metro will add two late-evening train services "
                "on the Blue Line from October. The operator expects shorter wait times."
            ),
            published_at="2026-01-12",
            source_url="https://synthetic.example/news/han-river-transit",
            metadata={"topic": "transport", "region": "seoul"},
        ),
        CorpusDocument(
            document_id="news-busan-port-weather",
            domain=Domain.NEWS,
            language="en",
            title="Synthetic storm delays Busan cargo departures",
            body=(
                "A fictional winter storm delayed cargo departures from Busan Port by "
                "six hours. Terminal operators expect the backlog to clear by Friday."
            ),
            published_at="2026-02-03",
            source_url="https://synthetic.example/news/busan-port-weather",
            metadata={"topic": "shipping", "region": "busan"},
        ),
        CorpusDocument(
            document_id="news-seoul-air-quality",
            domain=Domain.NEWS,
            language="en",
            title="Seoul publishes synthetic air-quality forecast",
            body=(
                "The fictional city forecast predicts moderate particulate levels across "
                "Seoul on Thursday, with better conditions after overnight rain."
            ),
            published_at="2026-02-18",
            source_url="https://synthetic.example/news/seoul-air-quality",
            metadata={"topic": "environment", "region": "seoul"},
        ),
        CorpusDocument(
            document_id="news-seoul-mobility-ko",
            domain=Domain.NEWS,
            language="ko",
            title="서울 모빌리티 시범 서비스 확대",
            body=(
                "가상의 서울 모빌리티 서비스가 강남과 판교를 연결하는 심야 셔틀을 "
                "확대합니다. 이용자는 앱에서 실시간 도착 정보를 확인할 수 있습니다."
            ),
            published_at="2026-03-01",
            source_url="https://synthetic.example/news/seoul-mobility-ko",
            metadata={"topic": "transport", "region": "seoul"},
        ),
        CorpusDocument(
            document_id="news-orbit-battery-ko",
            domain=Domain.NEWS,
            language="ko",
            title="오빗 모빌리티 배터리 재활용 센터 개소",
            body=(
                "가상의 오빗 모빌리티가 인천에 배터리 재활용 센터를 열었습니다. "
                "센터는 회수된 배터리의 소재를 분류하고 재사용 가능 여부를 평가합니다."
            ),
            published_at="2026-03-14",
            source_url="https://synthetic.example/news/orbit-battery-ko",
            metadata={"topic": "sustainability", "region": "incheon"},
        ),
        CorpusDocument(
            document_id="finance-orbit-q4-results",
            domain=Domain.FINANCE,
            language="en",
            title="Orbit Mobility synthetic fourth-quarter results",
            body=(
                "Fictional company Orbit Mobility reported fourth-quarter revenue of 240 "
                "million credits, up 18 percent year over year. Its battery-recycling unit "
                "reached positive operating income."
            ),
            published_at="2026-02-10",
            source_url="https://synthetic.example/finance/orbit-q4-results",
            metadata={"company": "Orbit Mobility", "report_type": "earnings"},
        ),
        CorpusDocument(
            document_id="finance-han-river-capex",
            domain=Domain.FINANCE,
            language="en",
            title="Han River Metro synthetic capital plan",
            body=(
                "Fictional Han River Metro approved a 2026 capital plan focused on train "
                "signalling upgrades and station accessibility. The plan allocates 80 million "
                "credits to the Blue Line."
            ),
            published_at="2026-01-20",
            source_url="https://synthetic.example/finance/han-river-capex",
            metadata={"company": "Han River Metro", "report_type": "capital-plan"},
        ),
        CorpusDocument(
            document_id="finance-nova-guidance",
            domain=Domain.FINANCE,
            language="en",
            title="Nova Logistics synthetic annual guidance",
            body=(
                "Fictional Nova Logistics expects annual revenue growth of 6 to 9 percent. "
                "Management cited port congestion and fuel prices as the primary risks to "
                "its shipping forecast."
            ),
            published_at="2026-02-28",
            source_url="https://synthetic.example/finance/nova-guidance",
            metadata={"company": "Nova Logistics", "report_type": "guidance"},
        ),
        CorpusDocument(
            document_id="finance-boreal-green-bond",
            domain=Domain.FINANCE,
            language="en",
            title="Boreal Energy synthetic green bond issuance",
            body=(
                "Fictional Boreal Energy issued a 500 million credit green bond. Proceeds "
                "will fund grid-scale battery storage and solar transmission projects."
            ),
            published_at="2026-03-05",
            source_url="https://synthetic.example/finance/boreal-green-bond",
            metadata={"company": "Boreal Energy", "report_type": "financing"},
        ),
        CorpusDocument(
            document_id="finance-orbit-risk-ko",
            domain=Domain.FINANCE,
            language="ko",
            title="오빗 모빌리티 가상 사업보고서 위험 요인",
            body=(
                "가상의 오빗 모빌리티 사업보고서는 배터리 원자재 가격과 공급망 지연을 "
                "주요 위험 요인으로 제시합니다. 회사는 재활용 소재 비중을 높일 계획입니다."
            ),
            published_at="2026-03-18",
            source_url="https://synthetic.example/finance/orbit-risk-ko",
            metadata={"company": "Orbit Mobility", "report_type": "risk-factors"},
        ),
    ]


def build_queries() -> list[SearchQuery]:
    """Return evaluation queries spanning both domains and languages."""

    return [
        SearchQuery(query_id="q-late-trains", query="late evening Blue Line trains", language="en"),
        SearchQuery(
            query_id="q-orbit-recycling", query="Orbit battery recycling income", language="en"
        ),
        SearchQuery(
            query_id="q-shipping-risks",
            query="shipping forecast port congestion risk",
            language="en",
        ),
        SearchQuery(
            query_id="q-metro-capital",
            query="Han River Metro capital spending",
            language="en",
            domain=Domain.FINANCE,
        ),
        SearchQuery(query_id="q-seoul-shuttle", query="서울 심야 셔틀", language="ko"),
        SearchQuery(query_id="q-orbit-risk", query="오빗 배터리 공급망 위험", language="ko"),
    ]


def build_judgments() -> list[RelevanceJudgment]:
    """Return graded relevance labels with a primary result and useful alternatives."""

    return [
        RelevanceJudgment(
            query_id="q-late-trains", document_id="news-han-river-transit", relevance=3
        ),
        RelevanceJudgment(
            query_id="q-late-trains", document_id="finance-han-river-capex", relevance=1
        ),
        RelevanceJudgment(
            query_id="q-orbit-recycling", document_id="finance-orbit-q4-results", relevance=3
        ),
        RelevanceJudgment(
            query_id="q-orbit-recycling", document_id="news-orbit-battery-ko", relevance=2
        ),
        RelevanceJudgment(
            query_id="q-orbit-recycling", document_id="finance-orbit-risk-ko", relevance=1
        ),
        RelevanceJudgment(
            query_id="q-shipping-risks", document_id="finance-nova-guidance", relevance=3
        ),
        RelevanceJudgment(
            query_id="q-shipping-risks", document_id="news-busan-port-weather", relevance=2
        ),
        RelevanceJudgment(
            query_id="q-metro-capital", document_id="finance-han-river-capex", relevance=3
        ),
        RelevanceJudgment(
            query_id="q-seoul-shuttle", document_id="news-seoul-mobility-ko", relevance=3
        ),
        RelevanceJudgment(
            query_id="q-orbit-risk", document_id="finance-orbit-risk-ko", relevance=3
        ),
        RelevanceJudgment(
            query_id="q-orbit-risk", document_id="finance-orbit-q4-results", relevance=1
        ),
    ]


def write_jsonl(
    records: Iterable[CorpusDocument | SearchQuery | RelevanceJudgment], path: Path
) -> None:
    """Write records as stable, newline-delimited JSON for source-control-friendly diffs."""

    serialized_records = [
        json.dumps(record.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        for record in records
    ]
    path.write_text("\n".join(serialized_records) + "\n", encoding="utf-8")


def generate_corpus(output_directory: Path = DEFAULT_OUTPUT_DIRECTORY) -> None:
    """Generate all corpus files, overwriting only generated synthetic fixtures."""

    output_directory.mkdir(parents=True, exist_ok=True)
    write_jsonl(build_documents(), output_directory / "documents.jsonl")
    write_jsonl(build_queries(), output_directory / "queries.jsonl")
    write_jsonl(build_judgments(), output_directory / "qrels.jsonl")


def parse_args() -> argparse.Namespace:
    """Parse the output-directory argument for the fixture generator."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIRECTORY)
    return parser.parse_args()


if __name__ == "__main__":
    generate_corpus(parse_args().output_dir)

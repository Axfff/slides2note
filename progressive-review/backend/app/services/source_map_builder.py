from app.models.source import ExtractedDocument, SourceFrame


class SourceMapBuilder:
    """Thin extension point for richer source-unit normalization later."""

    def build(self, extracted: ExtractedDocument) -> list[SourceFrame]:
        return extracted.source_frames


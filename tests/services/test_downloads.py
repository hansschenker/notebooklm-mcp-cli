"""Tests for services.downloads module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from notebooklm_tools.core.errors import ArtifactDownloadError
from notebooklm_tools.services.downloads import (
    VALID_ARTIFACT_TYPES,
    VALID_OUTPUT_FORMATS,
    download_all,
    download_async,
    download_sync,
    get_default_extension,
    sanitize_filename,
    validate_artifact_type,
    validate_audio_extension,
    validate_output_format,
)
from notebooklm_tools.services.errors import ServiceError, ValidationError


@pytest.fixture
def mock_client():
    client = MagicMock()
    # Set up async methods
    client.download_audio = AsyncMock(return_value="/tmp/audio.m4a")
    client.download_video = AsyncMock(return_value="/tmp/video.mp4")
    client.download_slide_deck = AsyncMock(return_value="/tmp/slides.pdf")
    client.download_infographic = AsyncMock(return_value="/tmp/infographic.png")
    client.download_quiz = AsyncMock(return_value="/tmp/quiz.json")
    client.download_flashcards = AsyncMock(return_value="/tmp/flashcards.json")
    # Sync methods
    client.download_report.return_value = "/tmp/report.md"
    client.download_mind_map.return_value = "/tmp/mindmap.json"
    client.download_data_table.return_value = "/tmp/table.csv"
    return client


class TestValidateArtifactType:
    """Test validate_artifact_type function."""

    @pytest.mark.parametrize("artifact_type", VALID_ARTIFACT_TYPES)
    def test_valid_types_pass(self, artifact_type):
        validate_artifact_type(artifact_type)  # should not raise

    def test_invalid_type_raises_validation_error(self):
        with pytest.raises(ValidationError, match="Unknown artifact type"):
            validate_artifact_type("podcast")


class TestValidateOutputFormat:
    """Test validate_output_format function."""

    @pytest.mark.parametrize("fmt", VALID_OUTPUT_FORMATS)
    def test_valid_formats_pass(self, fmt):
        validate_output_format(fmt)  # should not raise

    def test_invalid_format_raises_validation_error(self):
        with pytest.raises(ValidationError, match="Invalid output format"):
            validate_output_format("pdf")


class TestGetDefaultExtension:
    """Test get_default_extension function."""

    def test_audio_extension(self):
        assert get_default_extension("audio") == "m4a"

    def test_report_extension(self):
        assert get_default_extension("report") == "md"

    def test_quiz_default_json(self):
        assert get_default_extension("quiz") == "json"

    def test_quiz_markdown(self):
        assert get_default_extension("quiz", "markdown") == "md"

    def test_quiz_html(self):
        assert get_default_extension("quiz", "html") == "html"

    def test_flashcards_markdown(self):
        assert get_default_extension("flashcards", "markdown") == "md"


class TestDownloadSync:
    """Test download_sync for non-streaming artifacts."""

    def test_download_report(self, mock_client):
        result = download_sync(mock_client, "nb-1", "report", "/tmp/report.md")
        assert result["artifact_type"] == "report"
        assert result["path"] == "/tmp/report.md"

    def test_download_mind_map(self, mock_client):
        result = download_sync(mock_client, "nb-1", "mind_map", "/tmp/mm.json")
        assert result["path"] == "/tmp/mindmap.json"

    def test_download_data_table(self, mock_client):
        result = download_sync(mock_client, "nb-1", "data_table", "/tmp/t.csv")
        assert result["path"] == "/tmp/table.csv"

    def test_invalid_type_raises_validation_error(self, mock_client):
        with pytest.raises(ValidationError, match="Unknown"):
            download_sync(mock_client, "nb-1", "podcast", "/tmp/out")

    def test_streaming_type_raises_validation_error(self, mock_client):
        with pytest.raises(ValidationError, match="requires async"):
            download_sync(mock_client, "nb-1", "audio", "/tmp/out")

    def test_api_error_raises_service_error(self, mock_client):
        mock_client.download_report.side_effect = RuntimeError("fail")
        with pytest.raises(ServiceError, match="Failed to download"):
            download_sync(mock_client, "nb-1", "report", "/tmp/out")

    def test_falsy_path_raises_service_error(self, mock_client):
        mock_client.download_report.return_value = None
        with pytest.raises(ServiceError, match="returned no path"):
            download_sync(mock_client, "nb-1", "report", "/tmp/out")


class TestDownloadAsync:
    """Test download_async for streaming artifacts."""

    @pytest.mark.asyncio
    async def test_download_audio(self, mock_client):
        result = await download_async(mock_client, "nb-1", "audio", "/tmp/a.m4a")
        assert result["artifact_type"] == "audio"
        assert result["path"] == "/tmp/audio.m4a"

    @pytest.mark.asyncio
    async def test_download_video(self, mock_client):
        result = await download_async(mock_client, "nb-1", "video", "/tmp/v.mp4")
        assert result["path"] == "/tmp/video.mp4"

    @pytest.mark.asyncio
    async def test_download_slide_deck(self, mock_client):
        result = await download_async(mock_client, "nb-1", "slide_deck", "/tmp/s.pdf")
        assert result["path"] == "/tmp/slides.pdf"

    @pytest.mark.asyncio
    async def test_download_infographic(self, mock_client):
        result = await download_async(mock_client, "nb-1", "infographic", "/tmp/i.png")
        assert result["path"] == "/tmp/infographic.png"

    @pytest.mark.asyncio
    async def test_download_quiz_json(self, mock_client):
        result = await download_async(
            mock_client,
            "nb-1",
            "quiz",
            "/tmp/q.json",
            output_format="json",
        )
        assert result["path"] == "/tmp/quiz.json"

    @pytest.mark.asyncio
    async def test_download_flashcards_html(self, mock_client):
        result = await download_async(
            mock_client,
            "nb-1",
            "flashcards",
            "/tmp/f.html",
            output_format="html",
        )
        assert result["path"] == "/tmp/flashcards.json"

    @pytest.mark.asyncio
    async def test_invalid_type_raises_validation_error(self, mock_client):
        with pytest.raises(ValidationError, match="Unknown"):
            await download_async(mock_client, "nb-1", "podcast", "/tmp/out")

    @pytest.mark.asyncio
    async def test_invalid_format_for_quiz_raises_validation_error(self, mock_client):
        with pytest.raises(ValidationError, match="Invalid output format"):
            await download_async(
                mock_client,
                "nb-1",
                "quiz",
                "/tmp/out",
                output_format="pdf",
            )

    @pytest.mark.asyncio
    async def test_api_error_raises_service_error(self, mock_client):
        mock_client.download_audio = AsyncMock(side_effect=RuntimeError("fail"))
        with pytest.raises(ServiceError, match="Failed to download"):
            await download_async(mock_client, "nb-1", "audio", "/tmp/out")

    @pytest.mark.asyncio
    async def test_audio_propagation_error_has_specific_user_message(self, mock_client):
        error = ArtifactDownloadError(
            "audio",
            details="media download URL is still propagating; retry in a few minutes",
        )
        mock_client.download_audio = AsyncMock(side_effect=error)

        with pytest.raises(ServiceError) as exc_info:
            await download_async(mock_client, "nb-1", "audio", "/tmp/out.m4a")

        assert "still propagating" in exc_info.value.user_message

    @pytest.mark.asyncio
    async def test_falsy_path_raises_service_error(self, mock_client):
        mock_client.download_audio = AsyncMock(return_value=None)
        with pytest.raises(ServiceError, match="returned no path"):
            await download_async(mock_client, "nb-1", "audio", "/tmp/out")

    @pytest.mark.asyncio
    async def test_progress_callback_passed_through(self, mock_client):
        cb = MagicMock()
        await download_async(
            mock_client,
            "nb-1",
            "audio",
            "/tmp/a.m4a",
            progress_callback=cb,
        )
        # Verify the callback was passed to the client method
        mock_client.download_audio.assert_called_once_with(
            "nb-1",
            "/tmp/a.m4a",
            None,
            progress_callback=cb,
        )

    @pytest.mark.asyncio
    async def test_download_report_via_async(self, mock_client):
        """Issue #107: report must be downloadable via download_async."""
        result = await download_async(mock_client, "nb-1", "report", "/tmp/r.md")
        assert result["artifact_type"] == "report"
        assert result["path"] == "/tmp/report.md"
        mock_client.download_report.assert_called_once_with("nb-1", "/tmp/r.md", None)

    @pytest.mark.asyncio
    async def test_download_mind_map_via_async(self, mock_client):
        """Issue #107: mind_map must be downloadable via download_async."""
        result = await download_async(mock_client, "nb-1", "mind_map", "/tmp/mm.json")
        assert result["artifact_type"] == "mind_map"
        assert result["path"] == "/tmp/mindmap.json"
        mock_client.download_mind_map.assert_called_once_with("nb-1", "/tmp/mm.json", None)

    @pytest.mark.asyncio
    async def test_download_data_table_via_async(self, mock_client):
        """Issue #107: data_table must be downloadable via download_async."""
        result = await download_async(mock_client, "nb-1", "data_table", "/tmp/dt.csv")
        assert result["artifact_type"] == "data_table"
        assert result["path"] == "/tmp/table.csv"
        mock_client.download_data_table.assert_called_once_with("nb-1", "/tmp/dt.csv", None)


class TestValidateAudioExtension:
    """Test validate_audio_extension — Issue #185."""

    @pytest.mark.parametrize("ext", [".mp3", ".wav", ".ogg", ".flac", ".aiff", ".wma"])
    def test_mismatched_extensions_rejected(self, ext):
        with pytest.raises(ValidationError, match="cannot honor"):
            validate_audio_extension(f"/tmp/podcast{ext}")

    @pytest.mark.parametrize("ext", [".m4a", ".mp4", ".m4b"])
    def test_compatible_extensions_pass(self, ext):
        validate_audio_extension(f"/tmp/podcast{ext}")  # should not raise

    def test_no_extension_passes(self):
        validate_audio_extension("/tmp/podcast")  # should not raise

    def test_case_insensitive(self):
        with pytest.raises(ValidationError, match="cannot honor"):
            validate_audio_extension("/tmp/podcast.MP3")

    @pytest.mark.asyncio
    async def test_download_audio_rejects_mp3_async(self, mock_client):
        """Issue #185: download_async must reject .mp3 for audio."""
        with pytest.raises(ValidationError, match="cannot honor"):
            await download_async(mock_client, "nb-1", "audio", "/tmp/out.mp3")

    def test_download_audio_rejects_mp3_sync(self, mock_client):
        """Issue #185: download_sync must also reject .mp3 for audio."""
        with pytest.raises(ValidationError, match="cannot honor"):
            download_sync(mock_client, "nb-1", "audio", "/tmp/out.mp3")


class TestSanitizeFilename:
    """Test sanitize_filename function."""

    def test_invalid_chars_replaced(self):
        assert sanitize_filename('a<b>c:d"e/f\\g|h?i*j') == "a_b_c_d_e_f_g_h_i_j"

    def test_whitespace_collapsed(self):
        assert sanitize_filename("  My   Report\ttitle ") == "My Report title"

    def test_empty_returns_fallback(self):
        assert sanitize_filename("", fallback="report") == "report"

    def test_whitespace_only_returns_fallback(self):
        assert sanitize_filename("   ", fallback="report") == "report"

    def test_truncates_long_names(self):
        assert len(sanitize_filename("x" * 500)) == 80

    def test_trailing_dots_stripped(self):
        assert sanitize_filename("notes...") == "notes"

    def test_windows_reserved_names_prefixed(self):
        assert sanitize_filename("CON") == "_CON"


def _artifact(**overrides):
    base = {
        "artifact_id": "art-1",
        "type": "report",
        "title": "My Artifact",
        "status": "completed",
    }
    base.update(overrides)
    return base


def _echo_path_sync(notebook_id, output_path, artifact_id=None, *args, **kwargs):
    return output_path


async def _echo_path_async(notebook_id, output_path, artifact_id=None, *args, **kwargs):
    return output_path


@pytest.fixture
def bulk_client():
    """Client whose download methods return the requested output path."""
    client = MagicMock()
    for name in (
        "download_audio",
        "download_video",
        "download_slide_deck",
        "download_infographic",
        "download_quiz",
        "download_flashcards",
    ):
        setattr(client, name, AsyncMock(side_effect=_echo_path_async))
    for name in ("download_report", "download_mind_map", "download_data_table"):
        getattr(client, name).side_effect = _echo_path_sync
    return client


def _patch_lookups(monkeypatch, artifacts, title="My Notebook"):
    monkeypatch.setattr(
        "notebooklm_tools.services.downloads.get_studio_status",
        lambda client, nb: {
            "artifacts": artifacts,
            "total": len(artifacts),
            "completed": sum(1 for a in artifacts if a.get("status") == "completed"),
            "in_progress": sum(1 for a in artifacts if a.get("status") == "in_progress"),
        },
    )
    monkeypatch.setattr(
        "notebooklm_tools.services.downloads.get_notebook",
        lambda client, nb: {"notebook_id": nb, "title": title},
    )


class TestDownloadAll:
    """Test download_all — bulk download into a per-notebook directory."""

    @pytest.mark.asyncio
    async def test_downloads_all_completed_artifacts(self, bulk_client, monkeypatch, tmp_path):
        _patch_lookups(
            monkeypatch,
            [
                _artifact(artifact_id="a1", type="video", title="Overview Video"),
                _artifact(artifact_id="a2", type="report", title="Briefing"),
                _artifact(artifact_id="a3", type="mind_map", title="Map"),
                _artifact(artifact_id="a4", type="slide_deck", title="Deck"),
            ],
        )
        result = await download_all(bulk_client, "nb-1", str(tmp_path))

        assert result["downloaded"] == 4
        assert result["failed"] == 0
        assert result["skipped"] == []
        assert result["notebook_title"] == "My Notebook"
        assert result["output_dir"] == str(tmp_path / "My Notebook")
        paths = {item["artifact_type"]: item["path"] for item in result["items"]}
        assert paths["video"].endswith("Overview Video.mp4")
        assert paths["report"].endswith("Briefing.md")
        assert paths["mind_map"].endswith("Map.json")
        assert paths["slide_deck"].endswith("Deck.pdf")
        assert (tmp_path / "My Notebook").is_dir()

    @pytest.mark.asyncio
    async def test_skips_non_completed_artifacts(self, bulk_client, monkeypatch, tmp_path):
        _patch_lookups(
            monkeypatch,
            [
                _artifact(type="video", status="in_progress"),
                _artifact(type="audio", status="failed"),
            ],
        )
        result = await download_all(bulk_client, "nb-1", str(tmp_path))

        assert result["downloaded"] == 0
        assert result["failed"] == 0
        assert len(result["skipped"]) == 2
        assert "not completed" in result["skipped"][0]["reason"]

    @pytest.mark.asyncio
    async def test_types_filter(self, bulk_client, monkeypatch, tmp_path):
        _patch_lookups(
            monkeypatch,
            [
                _artifact(artifact_id="a1", type="video"),
                _artifact(artifact_id="a2", type="report"),
            ],
        )
        result = await download_all(bulk_client, "nb-1", str(tmp_path), artifact_types=["report"])

        assert result["downloaded"] == 1
        assert result["items"][0]["artifact_type"] == "report"
        assert result["skipped"][0]["reason"] == "type not requested"

    @pytest.mark.asyncio
    async def test_invalid_type_filter_raises(self, bulk_client, tmp_path):
        with pytest.raises(ValidationError, match="Unknown artifact type"):
            await download_all(bulk_client, "nb-1", str(tmp_path), artifact_types=["podcast"])

    @pytest.mark.asyncio
    async def test_one_failure_does_not_stop_others(self, bulk_client, monkeypatch, tmp_path):
        bulk_client.download_video = AsyncMock(side_effect=RuntimeError("boom"))
        _patch_lookups(
            monkeypatch,
            [
                _artifact(artifact_id="a1", type="video", title="Video"),
                _artifact(artifact_id="a2", type="report", title="Report"),
            ],
        )
        result = await download_all(bulk_client, "nb-1", str(tmp_path))

        assert result["downloaded"] == 1
        assert result["failed"] == 1
        failed = [item for item in result["items"] if not item["success"]]
        assert failed[0]["artifact_type"] == "video"
        assert failed[0]["error"]

    @pytest.mark.asyncio
    async def test_filename_collision_deduped(self, bulk_client, monkeypatch, tmp_path):
        _patch_lookups(
            monkeypatch,
            [
                _artifact(artifact_id="a1", type="report", title="Same"),
                _artifact(artifact_id="a2", type="report", title="Same"),
            ],
        )
        result = await download_all(bulk_client, "nb-1", str(tmp_path))

        names = sorted(
            item["path"].replace("\\", "/").rsplit("/", 1)[1] for item in result["items"]
        )
        assert names == ["Same.md", "Same_2.md"]

    @pytest.mark.asyncio
    async def test_directory_falls_back_to_notebook_id(self, bulk_client, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "notebooklm_tools.services.downloads.get_studio_status",
            lambda client, nb: {"artifacts": [], "total": 0, "completed": 0, "in_progress": 0},
        )

        def _raise(client, nb):
            raise ServiceError("nope")

        monkeypatch.setattr("notebooklm_tools.services.downloads.get_notebook", _raise)
        result = await download_all(bulk_client, "nb-1", str(tmp_path))

        assert result["notebook_title"] == "nb-1"
        assert result["output_dir"] == str(tmp_path / "nb-1")

    @pytest.mark.asyncio
    async def test_slide_format_pptx_extension(self, bulk_client, monkeypatch, tmp_path):
        _patch_lookups(monkeypatch, [_artifact(artifact_id="a1", type="slide_deck", title="Deck")])
        result = await download_all(bulk_client, "nb-1", str(tmp_path), slide_deck_format="pptx")

        assert result["items"][0]["path"].endswith("Deck.pptx")

    @pytest.mark.asyncio
    async def test_invalid_slide_format_raises(self, bulk_client, tmp_path):
        with pytest.raises(ValidationError, match="slide deck format"):
            await download_all(bulk_client, "nb-1", str(tmp_path), slide_deck_format="keynote")

    @pytest.mark.asyncio
    async def test_artifact_ids_passed_through(self, bulk_client, monkeypatch, tmp_path):
        _patch_lookups(monkeypatch, [_artifact(artifact_id="mm-7", type="mind_map", title="Map")])
        await download_all(bulk_client, "nb-1", str(tmp_path))

        args = bulk_client.download_mind_map.call_args
        assert args[0][0] == "nb-1"
        assert args[0][2] == "mm-7"

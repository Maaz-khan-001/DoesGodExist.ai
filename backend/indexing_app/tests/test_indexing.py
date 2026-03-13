import pytest
from indexing_app.chunkers import (
    normalise_stages,
    chunk_quran_verse,
    chunk_hadith,
    chunk_philosophy_argument,
    chunk_glossary_term,
    chunk_debate_topic,
)
from indexing_app.pipeline import IndexingPipeline
from rag_app.models import Document, DocumentChunk


# ── normalise_stages ──────────────────────────────────────────────────────────

class TestNormaliseStages:

    def test_integer_stages_mapped(self):
        assert normalise_stages([1]) == ['existence']
        assert normalise_stages([2]) == ['prophethood']
        assert normalise_stages([3]) == ['muhammad']
        assert normalise_stages([4]) == ['invitation']

    def test_verbose_string_stages_mapped(self):
        assert normalise_stages(['existence_of_god']) == ['existence']
        assert normalise_stages(['necessity_of_prophethood']) == ['prophethood']
        assert normalise_stages(['prophethood_of_muhammad']) == ['muhammad']
        assert normalise_stages(['invitation_to_islam']) == ['invitation']

    def test_mixed_int_and_string(self):
        result = normalise_stages([1, 'invitation_to_islam'])
        assert 'existence' in result
        assert 'invitation' in result

    def test_deduplication(self):
        result = normalise_stages([1, 1, 'existence_of_god'])
        assert result.count('existence') == 1

    def test_empty_input_defaults_to_existence(self):
        assert normalise_stages([]) == ['existence']

    def test_unknown_value_kept_as_cleaned_string(self):
        result = normalise_stages(['some_unknown_topic'])
        assert 'some_unknown_topic' in result

    def test_alias_monotheism_maps_to_existence(self):
        assert normalise_stages(['monotheism']) == ['existence']

    def test_alias_fitrah_maps_to_existence(self):
        assert normalise_stages(['fitrah']) == ['existence']


# ── chunk_quran_verse ─────────────────────────────────────────────────────────

class TestChunkQuranVerse:

    def _verse(self, **overrides):
        base = {
            'surah': 2,
            'ayah': 255,
            'reference': '2:255',
            'arabic': 'اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ',
            'translations': {
                'english': 'Allah — there is no deity except Him.',
                'urdu': 'اللہ کے سوا کوئی معبود نہیں',
            },
            'debate_stage_tags': ['existence_of_god'],
            'topic_tags': ['tawhid', 'monotheism'],
            'summary': 'Ayat al-Kursi',
            'theological_role': 'core',
            'usage_notes': 'Use for existence arguments',
            'confidence_level': 'highest',
        }
        base.update(overrides)
        return base

    def test_returns_one_chunk(self):
        chunks = chunk_quran_verse(self._verse())
        assert len(chunks) == 1

    def test_chunk_type_is_quran(self):
        chunk = chunk_quran_verse(self._verse())[0]
        assert chunk['chunk_type'] == 'quran'

    def test_english_content_present(self):
        chunk = chunk_quran_verse(self._verse())[0]
        assert 'Allah' in chunk['content']

    def test_arabic_content_preserved(self):
        chunk = chunk_quran_verse(self._verse())[0]
        assert chunk['content_arabic'] is not None

    def test_urdu_content_preserved(self):
        chunk = chunk_quran_verse(self._verse())[0]
        assert chunk['content_urdu'] is not None

    def test_stage_tags_normalised(self):
        chunk = chunk_quran_verse(self._verse())[0]
        assert 'existence' in chunk['stage_tags']

    def test_source_ref_contains_surah_and_ayah(self):
        chunk = chunk_quran_verse(self._verse())[0]
        assert chunk['source_ref']['surah'] == 2
        assert chunk['source_ref']['ayah'] == 255

    def test_is_verified_true(self):
        chunk = chunk_quran_verse(self._verse())[0]
        assert chunk['is_verified'] is True

    def test_token_count_positive(self):
        chunk = chunk_quran_verse(self._verse())[0]
        assert chunk['token_count'] > 0

    def test_missing_english_returns_empty(self):
        verse = self._verse()
        verse['translations'] = {'english': '', 'urdu': ''}
        assert chunk_quran_verse(verse) == []


# ── chunk_hadith ──────────────────────────────────────────────────────────────

class TestChunkHadith:

    def _hadith(self, **overrides):
        base = {
            'hadith_number': 1,
            'book': 'Book of Revelation',
            'book_number': 1,
            'full_text': {
                'english': 'Actions are judged by intentions.',
                'arabic': 'إِنَّمَا الأَعْمَالُ بِالنِّيَّاتِ',
                'urdu': 'اعمال کا دارومدار نیتوں پر ہے',
            },
            'authentication': 'Sahih',
            'confidence_level': 'highest',
            'stage': [1, 2],
            'debate_stage_tags': [],
            'topic_tags': ['intention', 'actions'],
            'summary': 'Importance of intention',
            'theological_role': 'foundational',
            'cross_references': [],
            'usage_notes': '',
        }
        base.update(overrides)
        return base

    def test_returns_one_chunk(self):
        assert len(chunk_hadith(self._hadith())) == 1

    def test_chunk_type_is_hadith(self):
        assert chunk_hadith(self._hadith())[0]['chunk_type'] == 'hadith'

    def test_sahih_is_verified(self):
        assert chunk_hadith(self._hadith(authentication='Sahih'))[0]['is_verified'] is True

    def test_hasan_is_verified(self):
        assert chunk_hadith(self._hadith(authentication='Hasan'))[0]['is_verified'] is True

    def test_daif_is_not_verified(self):
        assert chunk_hadith(self._hadith(authentication='Daif'))[0]['is_verified'] is False

    def test_stage_int_list_normalised(self):
        chunk = chunk_hadith(self._hadith(stage=[1, 2]))[0]
        assert 'existence' in chunk['stage_tags']
        assert 'prophethood' in chunk['stage_tags']

    def test_arabic_preserved(self):
        chunk = chunk_hadith(self._hadith())[0]
        assert chunk['content_arabic'] is not None

    def test_missing_english_returns_empty(self):
        h = self._hadith()
        h['full_text']['english'] = ''
        assert chunk_hadith(h) == []

    def test_source_ref_has_collection_and_number(self):
        chunk = chunk_hadith(self._hadith())[0]
        assert 'collection' in chunk['source_ref']
        assert 'number' in chunk['source_ref']


# ── chunk_philosophy_argument ─────────────────────────────────────────────────

class TestChunkPhilosophyArgument:

    def _argument(self, **overrides):
        base = {
            'name': 'Kalam Cosmological Argument',
            'category': 'cosmological',
            'core_claim': 'The universe had a beginning, therefore it has a cause.',
            'full_argument': 'Everything that begins to exist has a cause. The universe began. Therefore the universe has a cause.',
            'rebuttals': ['What caused God?'],
            'counter_rebuttals': ['God is uncaused by definition.'],
            'topic_tags': ['causality', 'cosmology'],
            'confidence_level': 'high',
        }
        base.update(overrides)
        return base

    def test_returns_one_chunk(self):
        assert len(chunk_philosophy_argument(self._argument(), stage_int=1)) == 1

    def test_chunk_type_is_philosophy(self):
        chunk = chunk_philosophy_argument(self._argument(), stage_int=1)[0]
        assert chunk['chunk_type'] == 'philosophy'

    def test_argument_name_in_content(self):
        chunk = chunk_philosophy_argument(self._argument(), stage_int=1)[0]
        assert 'Kalam' in chunk['content']

    def test_stage_correctly_set(self):
        chunk = chunk_philosophy_argument(self._argument(), stage_int=2)[0]
        assert 'prophethood' in chunk['stage_tags']

    def test_is_verified_false(self):
        # Philosophy arguments are always is_verified=False (they are human reasoning, not scripture)
        chunk = chunk_philosophy_argument(self._argument(), stage_int=1)[0]
        assert chunk['is_verified'] is False


# ── chunk_glossary_term ───────────────────────────────────────────────────────

class TestChunkGlossaryTerm:

    def test_dict_definition_parsed(self):
        chunks = chunk_glossary_term('Tawhid', {'definition': 'The oneness of God.', 'stage': 1})
        assert len(chunks) == 1
        assert 'Tawhid' in chunks[0]['content']
        assert 'existence' in chunks[0]['stage_tags']

    def test_plain_string_definition(self):
        chunks = chunk_glossary_term('Iman', 'Faith in Allah.')
        assert len(chunks) == 1
        assert 'Iman' in chunks[0]['content']
        # Plain string gets all stages
        assert 'existence' in chunks[0]['stage_tags']

    def test_empty_definition_returns_empty(self):
        assert chunk_glossary_term('Empty', {'definition': '', 'stage': 1}) == []

    def test_chunk_type_is_meta(self):
        chunks = chunk_glossary_term('Nabi', {'definition': 'A prophet.', 'stage': 2})
        assert chunks[0]['chunk_type'] == 'meta'

    def test_source_ref_has_term(self):
        chunks = chunk_glossary_term('Risalah', {'definition': 'Prophethood.', 'stage': 2})
        assert chunks[0]['source_ref']['term'] == 'Risalah'


# ── chunk_debate_topic ────────────────────────────────────────────────────────

class TestChunkDebateTopic:

    def _topic(self, **overrides):
        base = {
            'topic_id': 'does_god_exist',
            'category': 'metaphysics',
            'title': 'Does God Exist?',
            'description': 'Core question of the debate.',
            'key_questions': ['Why is there something rather than nothing?'],
            'supporting_arguments': ['Kalam', 'Fine-tuning'],
            'supporting_sources': ['Quran 2:255'],
            'transition_condition': 'user_accepts_god',
        }
        base.update(overrides)
        return base

    def test_returns_one_chunk(self):
        assert len(chunk_debate_topic(self._topic(), stage_str='existence')) == 1

    def test_title_in_content(self):
        chunk = chunk_debate_topic(self._topic(), stage_str='existence')[0]
        assert 'Does God Exist' in chunk['content']  # topic_id.replace('_',' ').title() — no '?'

    def test_stage_tag_set(self):
        chunk = chunk_debate_topic(self._topic(), stage_str='prophethood')[0]
        assert 'prophethood' in chunk['stage_tags']


# ── IndexingPipeline ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestIndexingPipeline:

    def _chunk_data(self, index=0):
        return {
            'content': f'Test content {index}',
            'content_arabic': None,
            'content_urdu': None,
            'chunk_type': 'philosophy',
            'token_count': 10,
            'stage_tags': ['existence'],
            'topic_tags': ['test'],
            'source_ref': {'ref': f'test_{index}'},
            'is_verified': True,
        }

    def test_ingest_creates_document(self):
        pipeline = IndexingPipeline()
        doc = pipeline.ingest_document(
            title='Test Document',
            source_type='philosophy',
            chunks_data=[self._chunk_data(0), self._chunk_data(1)],
        )
        assert Document.objects.filter(title='Test Document').exists()
        assert doc.indexing_status == 'complete'

    def test_ingest_creates_chunks(self):
        pipeline = IndexingPipeline()
        pipeline.ingest_document(
            title='Chunk Test',
            source_type='philosophy',
            chunks_data=[self._chunk_data(i) for i in range(3)],
        )
        doc = Document.objects.get(title='Chunk Test')
        assert DocumentChunk.objects.filter(document=doc).count() == 3

    def test_ingest_is_idempotent(self):
        pipeline = IndexingPipeline()
        chunks = [self._chunk_data(0)]
        pipeline.ingest_document(title='Idempotent Doc', source_type='philosophy', chunks_data=chunks)
        pipeline.ingest_document(title='Idempotent Doc', source_type='philosophy', chunks_data=chunks)
        assert Document.objects.filter(title='Idempotent Doc').count() == 1

    def test_chunk_count_saved_on_document(self):
        pipeline = IndexingPipeline()
        pipeline.ingest_document(
            title='Count Test',
            source_type='hadith',
            chunks_data=[self._chunk_data(i) for i in range(5)],
        )
        doc = Document.objects.get(title='Count Test')
        assert doc.chunk_count == 5

    def test_indexing_status_set_to_complete(self):
        pipeline = IndexingPipeline()
        doc = pipeline.ingest_document(
            title='Status Test',
            source_type='quran',
            chunks_data=[self._chunk_data(0)],
        )
        assert doc.indexing_status == 'complete'

    def test_checksum_is_deterministic(self):
        """Same title always produces same checksum, enabling idempotency."""
        import hashlib
        title = 'Deterministic Title'
        expected = hashlib.sha256(title.encode()).hexdigest()
        pipeline = IndexingPipeline()
        doc = pipeline.ingest_document(title=title, source_type='meta', chunks_data=[self._chunk_data()])
        assert doc.checksum == expected

    def test_empty_chunks_produces_no_chunk_records(self):
        pipeline = IndexingPipeline()
        doc = pipeline.ingest_document(
            title='Empty Chunks',
            source_type='philosophy',
            chunks_data=[],
        )
        assert DocumentChunk.objects.filter(document=doc).count() == 0
        assert doc.chunk_count == 0
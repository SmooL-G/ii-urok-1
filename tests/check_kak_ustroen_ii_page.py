import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "web" / "kak_ustroen_ii.html"
TOC = ROOT / "oglavlenie.html"
INDEX = ROOT / "index.html"
DEMOS = [
    "lenta_istorii.html",
    "vnimanie.html",
    "sleduyushchee_slovo.html",
    "tokenizator.html",
    "konstruktor_prompta.html",
    "kontekstnoe_okno.html",
    "vybor_instrumenta.html",
    "llm_arena.html",
]


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.id_counts = {}
        self.iframe_srcs = []
        self.imgs = []
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            self.id_counts[values["id"]] = self.id_counts.get(values["id"], 0) + 1
        if tag == "iframe" and values.get("src"):
            self.iframe_srcs.append(values["src"])
        if tag == "img":
            self.imgs.append(values)
        if tag == "a" and values.get("href"):
            self.hrefs.append(values["href"])


def parse(path):
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


class KakUstroenIiPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")
        cls.parser = parse(PAGE)

    def test_required_sections_and_unique_ids(self):
        required = {"hero", "about", "team", "lesson", "checklist", "quiz", "final"} | {f"s{i}" for i in range(1, 10)}
        self.assertTrue(required.issubset(self.parser.id_counts), required - set(self.parser.id_counts))
        duplicates = [key for key, count in self.parser.id_counts.items() if count > 1]
        self.assertEqual([], duplicates)

    def test_nav_links_point_to_existing_sections(self):
        anchors = {href[1:] for href in self.parser.hrefs if href.startswith("#")}
        missing = anchors - set(self.parser.id_counts)
        self.assertEqual(set(), missing)

    def test_lesson_markers_are_present(self):
        for marker in (
            "Тьюринг",
            "Attention Is All You Need",
            "Self-Attention",
            "генератор вероятностей",
            "Токен",
            "Роль · Контекст · Задача · Ограничения · Формат",
            "Контекстное окно",
            "Lost in the Middle",
            "Llama 4 Scout",
            "GigaChat",
            "YandexGPT",
            "DeepSeek",
            "Qwen",
            "Gemini",
            "LLM Arena",
            "светофор данных",
            "карточку проверки",
        ):
            self.assertIn(marker, self.html, marker)

    def test_course_info_and_team_come_first(self):
        order = [self.html.index(f'id="{key}"') for key in ("hero", "about", "team", "lesson", "s1")]
        self.assertEqual(sorted(order), order)
        self.assertIn("ДПО-1 «Основы применения <em>искусственного интеллекта</em>»", self.html)
        for marker in (
            "Сложные темы — разработка, внедрение в закрытый контур",
            "синтетических и обезличенных данных",
            "Шандалин Денис Анатольевич",
            "Курпичев Максим Анатольевич",
            "Чурилов Илья Владимирович",
            "Чепик Елена Юрьевна",
        ):
            self.assertIn(marker, self.html, marker)
        for photo in ("foto_shandalin", "foto_kurpichev", "foto_churilov", "foto_chepik"):
            self.assertTrue((ROOT / "png" / "kurs" / f"{photo}.jpg").is_file(), photo)

    def test_arena_link_in_llm_arena_section(self):
        s8 = self.html.split('id="s8"', 1)[1].split('id="s9"', 1)[0]
        self.assertIn('class="cta-link" href="https://arena.ai/"', s8)

    def test_meta_disclaimer_next_to_meta_mentions(self):
        self.assertIn("Meta признана экстремистской организацией", self.html)

    def test_services_have_active_links(self):
        for url in (
            "https://chatgpt.com/",
            "https://chat.deepseek.com/",
            "https://giga.chat/",
            "https://chat.qwen.ai/",
            "https://gemini.google.com/",
            "https://alice.yandex.ru/",
            "https://arena.ai/",
            "https://tiktoken.vercel.app/",
            "https://arxiv.org/abs/2307.03172",
        ):
            self.assertIn(f'href="{url}"', self.html, url)

    def test_external_links_open_safely(self):
        for match in re.finditer(r'<a [^>]*href="https?://[^"]+"[^>]*>', self.html):
            tag = match.group(0)
            self.assertIn('target="_blank"', tag, tag)
            self.assertIn('rel="noopener"', tag, tag)

    def test_all_demos_embedded_and_exist(self):
        self.assertTrue(set(DEMOS).issubset(self.parser.iframe_srcs))
        for demo in DEMOS:
            self.assertTrue((ROOT / "web" / demo).is_file(), demo)
            self.assertIn(f'data-fs-src="{demo}"', self.html, demo)

    def test_images_exist_have_alt_and_placeholder(self):
        self.assertGreaterEqual(len(self.parser.imgs), 20)  # остальные слайды — внутри ленты истории
        for img in self.parser.imgs:
            src = img.get("src", "")
            if not src:
                continue  # картинка лайтбокса заполняется скриптом
            self.assertTrue(src.startswith(("../png/kak_ustroen_ii/", "../png/kurs/")), src)
            self.assertTrue((PAGE.parent / src).resolve().is_file(), src)
            self.assertTrue(img.get("alt"), src)
            self.assertIn("img-missing", img.get("onerror", ""), src)

    def test_all_lesson_images_are_used(self):
        used = {Path(img["src"]).name for img in self.parser.imgs if img.get("src")}
        for demo in DEMOS:
            demo_html = (ROOT / "web" / demo).read_text(encoding="utf-8")
            used |= set(re.findall(r"\d\d_[a-z0-9_]+\.jpg", demo_html))
        on_disk = {path.name for path in (ROOT / "png" / "kak_ustroen_ii").glob("*.jpg")}
        self.assertEqual(set(), on_disk - used)

    def test_pages_are_self_contained(self):
        for path in [PAGE, TOC] + [ROOT / "web" / demo for demo in DEMOS]:
            html = path.read_text(encoding="utf-8")
            self.assertIn('lang="ru"', html, path.name)
            for forbidden in ("<script src=", "<link rel=\"stylesheet\"", "cdn.", "unpkg", "jsdelivr", "fonts.googleapis"):
                self.assertNotIn(forbidden, html, f"{path.name}: {forbidden}")

    def test_checklist_and_quiz(self):
        self.assertIn('const CHECKLIST_KEY = "dpo1-urok1-kak-ustroen-ii-checklist"', self.html)
        self.assertGreaterEqual(self.html.count("data-checklist-item="), 10)
        questions = re.findall(r'class="quiz-question" data-quiz="(\d+)"', self.html)
        self.assertEqual(7, len(questions))
        for index in questions:
            block = self.html.split(f'data-quiz="{index}"', 1)[1].split("quiz-feedback", 1)[0]
            self.assertEqual(1, block.count('value="right"'), index)

    def test_links_between_pages(self):
        self.assertIn('href="../oglavlenie.html"', self.html)
        toc = TOC.read_text(encoding="utf-8")
        self.assertIn('href="web/kak_ustroen_ii.html"', toc)
        for demo in DEMOS:
            self.assertIn(f'href="web/{demo}"', toc, demo)
        self.assertIn("web/kak_ustroen_ii.html", INDEX.read_text(encoding="utf-8"))


class TeacherNotesTest(unittest.TestCase):
    NOTES = ROOT / "web" / "konspekt_prepodavatelya.html"

    @classmethod
    def setUpClass(cls):
        cls.html = cls.NOTES.read_text(encoding="utf-8")
        cls.parser = parse(cls.NOTES)
        cls.lesson_ids = set(parse(PAGE).id_counts)

    def test_notes_are_self_contained(self):
        self.assertIn('lang="ru"', self.html)
        for forbidden in ("<script src=", "<link rel=\"stylesheet\"", "cdn."):
            self.assertNotIn(forbidden, self.html)

    def test_timeline_covers_ninety_minutes(self):
        for marker in ("00–02", "42–54", "86–90", "Ответы на квиз", "Частые вопросы слушателей"):
            self.assertIn(marker, self.html, marker)
        blocks = {key for key in self.parser.id_counts if re.fullmatch(r"b\d+", key)}
        self.assertEqual({f"b{i}" for i in range(11)}, blocks)

    def test_links_to_lesson_and_demos_resolve(self):
        for href in self.parser.hrefs:
            if href == "#":
                continue  # кнопка «Распечатать»
            if href.startswith("#"):
                self.assertIn(href[1:], self.parser.id_counts, href)
            elif href.startswith("kak_ustroen_ii.html#"):
                self.assertIn(href.split("#", 1)[1], self.lesson_ids, href)
            elif href.endswith(".html") and not href.startswith("http"):
                self.assertTrue((self.NOTES.parent / href).resolve().is_file(), href)
        self.assertIn('href="web/konspekt_prepodavatelya.html"', TOC.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

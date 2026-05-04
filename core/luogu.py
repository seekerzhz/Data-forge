from __future__ import annotations

import json
import re
import time

import requests
from bs4 import BeautifulSoup

from core.models import ProblemMeta, SampleCase


class LuoguClient:
    BASE = "https://www.luogu.com.cn/problem/"

    def __init__(self, cookie: str | None = None, delay_s: float = 1.0):
        self.delay_s = delay_s
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
        )
        if cookie:
            self.session.headers["Cookie"] = cookie

    @staticmethod
    def normalize_pid(problem: str) -> str:
        m = re.search(r"(P\d+)", problem.strip(), flags=re.IGNORECASE)
        if not m:
            raise ValueError("无法识别题号，请输入如 P1001 或完整题目链接")
        return m.group(1).upper()

    def fetch(self, problem: str) -> ProblemMeta:
        pid = self.normalize_pid(problem)
        url = f"{self.BASE}{pid}"
        time.sleep(self.delay_s)
        resp = self.session.get(url, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        next_data = self._extract_next_data(soup)
        if next_data:
            return self._parse_from_next_data(pid, next_data)
        return self._parse_from_html(pid, soup)

    @staticmethod
    def _extract_next_data(soup: BeautifulSoup) -> dict | None:
        node = soup.find("script", id="__NEXT_DATA__")
        if not node or not node.string:
            return None
        try:
            return json.loads(node.string)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _extract_samples_from_markdown(md: str) -> list[SampleCase]:
        samples: list[SampleCase] = []
        pattern = re.compile(
            r"###\s*输入\s*#?\d+\s*```\s*(.*?)\s*```\s*###\s*输出\s*#?\d+\s*```\s*(.*?)\s*```",
            flags=re.DOTALL,
        )
        for m in pattern.finditer(md):
            samples.append(SampleCase(input_data=m.group(1).strip(), output_data=m.group(2).strip()))
        return samples

    def _parse_from_next_data(self, pid: str, payload: dict) -> ProblemMeta:
        page = payload.get("props", {}).get("pageProps", {})
        current_data = page.get("data", {}).get("problem", {}) or page.get("currentData", {}).get("problem", {})
        title = current_data.get("title") or pid
        limits = current_data.get("limits", {})
        time_limit = f"{limits.get('time', 1000)}ms" if limits.get("time") else "1s"
        memory_limit = f"{limits.get('memory', 128)}MB" if limits.get("memory") else "128MB"

        content = current_data.get("content", {})
        if isinstance(content, str):
            content = {"description": content}

        description = content.get("description") or content.get("statement") or content.get("problemDescription") or ""
        input_spec = content.get("input") or content.get("inputFormat") or content.get("input_description") or ""
        output_spec = content.get("output") or content.get("outputFormat") or content.get("output_description") or ""

        tags = [x.get("name", "") for x in (current_data.get("tags") or []) if x.get("name")]
        samples_raw = content.get("samples") or current_data.get("samples") or []
        samples = [SampleCase(input_data=s.get("input", ""), output_data=s.get("output", "")) for s in samples_raw if isinstance(s, dict)]

        statement_md = current_data.get("translation", "") or current_data.get("statement", "") or ""
        if not statement_md:
            statement_md = f"## 题目描述\n\n{description}"
        if not samples:
            samples = self._extract_samples_from_markdown(statement_md)
        if "输入格式" not in statement_md and input_spec:
            statement_md += f"\n\n## 输入格式\n\n{input_spec}"
        if "输出格式" not in statement_md and output_spec:
            statement_md += f"\n\n## 输出格式\n\n{output_spec}"

        return ProblemMeta(pid=pid, title=title, time_limit=time_limit, memory_limit=memory_limit, description=description, input_spec=input_spec, output_spec=output_spec, statement_markdown=statement_md, tags=tags, samples=samples)

    def _parse_from_html(self, pid: str, soup: BeautifulSoup) -> ProblemMeta:
        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else pid
        limits = soup.find_all("span")
        limit_text = " ".join(x.get_text(" ", strip=True) for x in limits)
        time_limit = self._extract_with_fallback(limit_text, r"时间限制\s*([0-9]+\s*(?:ms|s))", "1s")
        memory_limit = self._extract_with_fallback(limit_text, r"内存限制\s*([0-9]+\s*(?:MB|MB?))", "128MB")
        sections = self._parse_sections(soup)
        description = sections.get("题目描述", "")
        input_spec = sections.get("输入格式", "")
        output_spec = sections.get("输出格式", "")
        samples = self._parse_samples(soup)
        tags = [x.get_text(strip=True) for x in soup.select("a[href*='/tag/']")]
        statement_md = f"# {title}\n\n## 题目描述\n\n{description}\n\n## 输入格式\n\n{input_spec}\n\n## 输出格式\n\n{output_spec}\n"
        return ProblemMeta(pid=pid, title=title, time_limit=time_limit, memory_limit=memory_limit, description=description, input_spec=input_spec, output_spec=output_spec, statement_markdown=statement_md, tags=tags, samples=samples)

    @staticmethod
    def _extract_with_fallback(text: str, pattern: str, fallback: str) -> str:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        return m.group(1) if m else fallback

    @staticmethod
    def _parse_sections(soup: BeautifulSoup) -> dict[str, str]:
        result: dict[str, str] = {}
        for h in soup.find_all(["h2", "h3"]):
            key = h.get_text(strip=True)
            parts: list[str] = []
            for sib in h.find_next_siblings():
                if sib.name in ("h2", "h3"):
                    break
                parts.append(sib.get_text("\n", strip=True))
            if parts:
                result[key] = "\n\n".join([x for x in parts if x])
        return result

    @staticmethod
    def _parse_samples(soup: BeautifulSoup) -> list[SampleCase]:
        pres = [p.get_text("\n", strip=False).strip("\n") for p in soup.find_all("pre")]
        return [SampleCase(input_data=pres[i], output_data=pres[i + 1]) for i in range(0, len(pres) - 1, 2)]


def fallback_from_raw(pid: str, title: str, raw_text: str) -> ProblemMeta:
    chunks: dict[str, str] = {"题目描述": ""}
    current = "题目描述"
    for line in raw_text.splitlines():
        if line.strip() in {"题目描述", "输入格式", "输出格式"}:
            current = line.strip()
            chunks.setdefault(current, "")
            continue
        chunks[current] += line + "\n"
    statement_md = raw_text.strip()
    samples = LuoguClient._extract_samples_from_markdown(statement_md)
    return ProblemMeta(pid=pid, title=title, time_limit="1s", memory_limit="128MB", description=chunks.get("题目描述", "").strip(), input_spec=chunks.get("输入格式", "").strip(), output_spec=chunks.get("输出格式", "").strip(), statement_markdown=statement_md, samples=samples)

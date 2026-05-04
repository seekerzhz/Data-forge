from __future__ import annotations

import re
import time
from typing import Any

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
        problem = problem.strip()
        m = re.search(r"(P\d+)", problem, flags=re.IGNORECASE)
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

        return ProblemMeta(
            pid=pid,
            title=title,
            time_limit=time_limit,
            memory_limit=memory_limit,
            description=description,
            input_spec=input_spec,
            output_spec=output_spec,
            tags=tags,
            samples=samples,
        )

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
        samples: list[SampleCase] = []
        for i in range(0, len(pres) - 1, 2):
            samples.append(SampleCase(input_data=pres[i], output_data=pres[i + 1]))
        return samples


def fallback_from_raw(pid: str, title: str, raw_text: str) -> ProblemMeta:
    chunks: dict[str, str] = {}
    current = "题目描述"
    chunks[current] = ""
    for line in raw_text.splitlines():
        if line.strip() in {"题目描述", "输入格式", "输出格式"}:
            current = line.strip()
            chunks.setdefault(current, "")
            continue
        chunks[current] += line + "\n"
    return ProblemMeta(
        pid=pid,
        title=title,
        time_limit="1s",
        memory_limit="128MB",
        description=chunks.get("题目描述", "").strip(),
        input_spec=chunks.get("输入格式", "").strip(),
        output_spec=chunks.get("输出格式", "").strip(),
    )

# 프로젝트 작업 지침

## 쇼핑 쇼츠 제작

쇼핑 쇼츠 제작, TikTok 상품 영상 수집, 원본 자막 블러, 한국어 나레이션 합성 또는 썸네일 제작 요청에는 `youtube-shorts` 스킬을 사용한다.
작업 전에 [.agents/skills/youtube-shorts/SKILL.md](.agents/skills/youtube-shorts/SKILL.md)를 읽고 V12 제작 절차와 검수 기준을 따른다. 스킬 폴더의 `AGENTS.md`도 확인한다.

- 스킬 위치: `.agents/skills/youtube-shorts/`
- 설치 스크립트: `.agents/skills/youtube-shorts/setup.py`
- 실행 스크립트: `.agents/skills/youtube-shorts/scripts/`
- 글꼴 및 음성 정렬 모델: `.agents/skills/youtube-shorts/assets/`

스킬 문서의 상대 경로는 스킬 폴더 기준으로 해석한다. Python 3.10 이상과 ffmpeg/ffprobe가 필요하다. `setup.py`는 직접 실행하는 설치 도우미이며 Python 패키지 빌드 설정이 아니다.
외부 서비스 API, API 키, API TTS 및 `.env` 설정을 요구하지 않는다. 씬별 한국어 WAV 나레이션은 로컬 파일로 준비한다. 상품 정보와 음성이 부족하면 필요한 입력만 요청한다.
기존 스크립트와 리소스를 임의로 변경하거나 삭제하지 않는다. 실제 제작 결과는 제품별 작업 폴더에 저장하고 ZIP으로 만들지 않는다.

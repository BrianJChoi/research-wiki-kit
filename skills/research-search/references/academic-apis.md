# 학술 API 호출

2026-11-05 확인. 공식 문서의 요금과 응답 헤더가 우선합니다.
Windows PowerShell에서는 `curl.exe`, Mac·Git Bash에서는 `curl`을 사용합니다. `--get --data-urlencode`로 검색어를 인코딩하고, HTTP 상태를 확인합니다. 결과 5개만 읽고 호출 사이 3초 이상 쉽니다. jq나 Python 설치를 요구하지 않습니다.

## Consensus

Consensus 계정을 만들고 Claude 커넥터에서 연결합니다. https://consensus.app 에서 시작합니다. 이 계정 연결을 설치 스크립트가 자동으로 대신하지 않습니다. 연결된 도구만 사용하며 Code 탭에서 커넥터가 보이지 않으면 건너뜁니다. 무료 계정 한도와 Code 탭 지원은 Windows 실기 확인 대상입니다.

## Crossref (키 없음)

```sh
curl --fail-with-body --get 'https://api.crossref.org/works' --data-urlencode 'query.bibliographic=retrieval augmented generation' --data-urlencode 'rows=5' --data-urlencode 'select=DOI,title,author,published,container-title,is-referenced-by-count,URL'
```

`message.items`의 DOI, title, author, published, `container-title`(학술지명), `is-referenced-by-count`(Crossref에 등록된 인용수)를 읽습니다. 초록이 없으면 `[서지만]`입니다.
사용자가 자신의 이메일을 환경 변수 `CROSSREF_MAILTO`에 설정했다면 Bash에서는 `--data-urlencode "mailto=$CROSSREF_MAILTO"`, PowerShell에서는 `--data-urlencode "mailto=$env:CROSSREF_MAILTO"`를 추가해 polite pool을 사용합니다. 이메일이 없으면 위 public 요청 그대로 진행합니다. 개인 이메일은 결과 리포트·시험 기록에 쓰지 않습니다. 요청 간 3초 이상 간격을 둡니다.
공식 근거: https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/ · https://www.crossref.org/documentation/retrieve-metadata/rest-api/

## arXiv

```sh
curl --fail-with-body --get 'https://export.arxiv.org/api/query' --data-urlencode 'search_query=all:"retrieval augmented generation"' --data-urlencode 'max_results=5' --data-urlencode 'sortBy=relevance'
```

응답 XML의 title, summary, published, id를 읽습니다. 프리프린트이므로 동료평가 여부를 구분합니다. HTML 원문 `https://arxiv.org/html/<id>`가 없으면 초록만 읽었음을 표시합니다.
공식 안내: https://info.arxiv.org/help/api/user-manual.html

## Semantic Scholar

**선택 경로입니다. 사용자의 `SEMANTIC_SCHOLAR_API_KEY`가 설정돼 있을 때만 호출합니다.** 아래 명령은 Bash 예시입니다. PowerShell에서는 `curl.exe`와 `$env:SEMANTIC_SCHOLAR_API_KEY`를 씁니다.

```sh
curl --fail-with-body --get 'https://api.semanticscholar.org/graph/v1/paper/search' -H "x-api-key: $SEMANTIC_SCHOLAR_API_KEY" --data-urlencode 'query=retrieval augmented generation' --data-urlencode 'limit=5' --data-urlencode 'fields=title,year,citationCount,abstract,externalIds,openAccessPdf,url,authors'
```

429면 재시도를 반복하지 않고 이 경로를 건너뜁니다. 다른 검색원으로 진행하며 보고서에 적습니다.
공식 안내: https://api.semanticscholar.org/api-docs/graph

## OpenAlex

**선택 경로입니다. 사용자의 `OPENALEX_API_KEY`가 설정돼 있을 때만 호출합니다. 키 없이는 호출하지 않습니다.**

키 없이는 같은 IP의 하루 $0.10을 나눠 씁니다. 검색 요청당 $0.001이면 약 100회입니다. 단건 조회와 필터 등은 비용이 다를 수 있습니다. 무료 개인 키는 하루 $1을 줍니다. 강의실에서는 각자 키 사용을 권합니다.

1. https://openalex.org 에서 무료 계정을 만듭니다.
2. 이메일 인증을 마친 뒤 https://openalex.org/settings/api 에서 키를 받습니다.
3. 개인 환경 변수 `OPENALEX_API_KEY`로 저장합니다. 채팅·노트·명령 실행 로그에 키를 출력하지 않습니다. 키 설정이 어렵다면 이 경로를 건너뛰고 기본 검색 순서로 진행합니다.
4. 무료 한도를 넘어 유료 크레딧을 자동 구매하지 않습니다. 429·한도 초과는 건너뛰고 표시합니다.

개인 키로 검색 (Bash):

```sh
curl --fail-with-body --get 'https://api.openalex.org/works' -H "Authorization: Bearer $OPENALEX_API_KEY" --data-urlencode 'search=retrieval augmented generation' --data-urlencode 'per_page=5' --data-urlencode 'select=id,doi,title,publication_year,cited_by_count,open_access,authorships'
```

키가 설정돼 있으면 같은 요청에 Authorization 헤더를 추가합니다. Bash는 `-H "Authorization: Bearer $OPENALEX_API_KEY"`, PowerShell은 `-H "Authorization: Bearer $env:OPENALEX_API_KEY"`입니다. 명령 추적·verbose를 켜지 않습니다.
응답의 남은 예산 헤더와 `meta.cost_usd`를 확인합니다. 키를 썼어도 429가 나면 멈춥니다.
공식 근거: https://help.openalex.org/api/authentication/ · https://help.openalex.org/access/pricing/ · https://help.openalex.org/access/example-costs/

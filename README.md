# Amazon 구매 데이터와 US Census ACS 통합 분석

## 프로젝트 개요
Amazon 구매 거래 데이터와 미국 Census ACS(5-year American Community Survey) 데이터를 결합하여 주별 소비 패턴과 지역별 인구 통계 상관관계를 분석하는 파이프라인입니다.

## 기안서 요약
- 목적: Amazon 구매 데이터의 주별 지출 패턴을 ACS 주별 사회경제 지표와 결합해 분석
- 데이터: `amazon-purchases.csv`, `survey.csv` 및 Census API에서 가져온 ACS 2022년 주별 지표
- 주요 분석:
  - 주별 Amazon 소비 지출 요약
  - 주별 카테고리별 지출 비중
  - ACS 지표(중간 소득, 대학 이상 학력 비율, 빈곤율, 히스패닉 비율)와 카테고리 지출 비율 간 상관관계
  - 설문 응답의 소득 대표성 및 편향 분석

## 사용된 파일
- `amazon_census_analysis.py`: 전체 데이터 로딩, 처리, ACS 호출, 합병, 분석, 결과 저장을 수행하는 메인 스크립트
- `amazon-purchases.csv`: Amazon 주문 내역 데이터
- `survey.csv`: 설문 응답 데이터

## 분석 흐름
1. Amazon 구매 데이터 로딩 및 정제
2. 설문 데이터 로딩 및 상태 코드 매핑
3. Census API로 ACS 주별 프로파일 수집
4. 주별 Amazon 지출 요약 및 카테고리별 지출 비율 계산
5. Amazon 주별 요약과 ACS 주별 지표 결합
6. 설문 응답 소득 편향 분석
7. 카테고리 지출 비율과 인구 통계 지표 간 Pearson 상관분석

## 주요 결과 파일
- `acs_2022_state_profile.csv`: ACS 주별 지표
- `amazon_acs_state_profile.csv`: Amazon 주별 요약
- `amazon_acs_merged.csv`: Amazon 요약과 ACS 지표 결합 결과
- `survey_bias_vs_acs.csv`: 설문 소득 편향 분석 결과
- `amazon_state_category_share.csv`: 주별 카테고리 지출 비중
- `amazon_acs_correlation_summary.csv`: 인구 통계 지표와 카테고리 지출 비율 상관관계 결과

## 실행 방법
```powershell
python amazon_census_analysis.py
```

> 주의: Census API 키가 스크립트 내 `DEFAULT_CENSUS_API_KEY`로 설정되어 있어야 합니다.

## 기안서 반영 사항
- 분석 목적과 데이터 흐름을 README에 명확히 정리
- 기존 스크립트의 안정성을 개선하여 경고 및 오류를 해결
- 결과 파일 생성과 상관분석 결과 저장 과정을 문서화

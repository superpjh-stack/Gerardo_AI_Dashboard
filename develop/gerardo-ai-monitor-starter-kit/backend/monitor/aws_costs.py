"""Read-only AWS Cost Explorer billing summary."""
from __future__ import annotations

import os
from datetime import date, timedelta


def monthly_costs(today: date | None = None) -> dict:
    today = today or date.today()
    start = today.replace(day=1)
    end = today + timedelta(days=1)  # Cost Explorer's end date is exclusive.
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, PartialCredentialsError
    except ImportError:
        return _unavailable('dependency_missing', 'AWS 비용 조회 모듈이 설치되지 않았습니다.')

    try:
        client = boto3.client('ce', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        response = client.get_cost_and_usage(
            TimePeriod={'Start': start.isoformat(), 'End': end.isoformat()},
            Granularity='DAILY', Metrics=['UnblendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}],
        )
    except (NoCredentialsError, PartialCredentialsError):
        return _unavailable('not_configured', 'AWS 자격증명을 찾을 수 없습니다. IAM 역할, AWS_PROFILE 또는 AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY를 설정하세요.')
    except ClientError as exc:
        code = exc.response.get('Error', {}).get('Code', 'AWS 오류')
        message = ('Cost Explorer 조회 권한이 없습니다. ce:GetCostAndUsage 권한을 확인하세요.'
                   if code in ('AccessDenied', 'AccessDeniedException', 'UnauthorizedException')
                   else f'AWS 비용 조회 실패: {code}')
        return _unavailable('error', message)
    except BotoCoreError:
        return _unavailable('error', 'AWS에 연결하지 못했습니다. 네트워크와 자격증명을 확인하세요.')

    daily: dict[str, float] = {}
    services: dict[str, float] = {}
    for result in response.get('ResultsByTime', []):
        day = result['TimePeriod']['Start']
        amount = sum(float(group['Metrics']['UnblendedCost']['Amount'])
                     for group in result.get('Groups', []))
        daily[day] = daily.get(day, 0.0) + amount
        for group in result.get('Groups', []):
            name = group.get('Keys', ['기타'])[0]
            services[name] = services.get(name, 0.0) + float(group['Metrics']['UnblendedCost']['Amount'])
    ordered_services = sorted(services.items(), key=lambda item: item[1], reverse=True)
    return {
        'status': 'connected', 'message': None, 'currency': 'USD',
        'period': {'start': start.isoformat(), 'end': end.isoformat()},
        'total': sum(daily.values()),
        'daily': [{'date': day, 'amount': amount} for day, amount in sorted(daily.items())],
        'services': [{'name': name, 'amount': amount} for name, amount in ordered_services],
        'updated_at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
    }


def _unavailable(status: str, message: str) -> dict:
    return {'status': status, 'message': message, 'currency': 'USD', 'period': None,
            'total': None, 'daily': [], 'services': [], 'updated_at': None}

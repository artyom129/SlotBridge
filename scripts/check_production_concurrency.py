from __future__ import annotations

import asyncio
import json
import os
from datetime import date, timedelta
from urllib.parse import urlsplit
from uuid import uuid4

import httpx


async def _register_and_login(client: httpx.AsyncClient, suffix: str) -> str:
    email = f"deployment-concurrency-{suffix}-{uuid4()}@example.com"
    password = f"ProductionE2E!{uuid4().hex}"
    registration = await client.post(
        "/auth/register",
        json={
            "first_name": "Production",
            "last_name": "Concurrency",
            "email": email,
            "password": password,
        },
    )
    registration.raise_for_status()
    login = await client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    login.raise_for_status()
    return login.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _find_slot(
    client: httpx.AsyncClient, token: str
) -> tuple[dict[str, str], str]:
    headers = _headers(token)
    organizations = (
        await client.get("/organizations", headers=headers)
    ).raise_for_status().json()
    organization = next(
        item for item in organizations if item.get("slug") == "slotbridge-demo"
    )
    organization_id = organization["id"]
    branches = (
        await client.get(
            f"/organizations/{organization_id}/branches", headers=headers
        )
    ).raise_for_status().json()
    services = (
        await client.get(
            f"/organizations/{organization_id}/services", headers=headers
        )
    ).raise_for_status().json()
    employees = (
        await client.get(
            f"/organizations/{organization_id}/employees", headers=headers
        )
    ).raise_for_status().json()

    for service in services:
        for employee in employees:
            if employee["branch_id"] != branches[0]["id"]:
                continue
            employee_services = (
                await client.get(
                    f"/employees/{employee['id']}/services", headers=headers
                )
            ).raise_for_status().json()
            if not any(item["id"] == service["id"] for item in employee_services):
                continue
            for offset in range(1, 15):
                requested_date = (date.today() + timedelta(days=offset)).isoformat()
                availability = (
                    await client.get(
                        "/availability",
                        headers=headers,
                        params={
                            "branch_id": branches[0]["id"],
                            "employee_id": employee["id"],
                            "service_id": service["id"],
                            "date": requested_date,
                        },
                    )
                ).raise_for_status().json()
                if availability["slots"]:
                    return (
                        {
                            "branch_id": branches[0]["id"],
                            "employee_id": employee["id"],
                            "service_id": service["id"],
                        },
                        availability["slots"][0]["start"],
                    )
    raise RuntimeError("No production slot is available for the concurrency check")


async def main() -> None:
    base_url = os.environ.get("SLOTBRIDGE_PRODUCTION_API_URL", "").rstrip("/")
    parsed = urlsplit(base_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise SystemExit("SLOTBRIDGE_PRODUCTION_API_URL must be a public HTTPS URL")

    async with httpx.AsyncClient(base_url=base_url, timeout=90) as client:
        readiness = await client.get("/api/v1/health/ready")
        readiness.raise_for_status()
        first_token, second_token = await asyncio.gather(
            _register_and_login(client, "a"),
            _register_and_login(client, "b"),
        )
        resource_ids, starts_at = await _find_slot(client, first_token)
        payload = {**resource_ids, "starts_at": starts_at}

        async def book(token: str) -> httpx.Response:
            return await client.post(
                "/appointments",
                headers={
                    **_headers(token),
                    "Idempotency-Key": str(uuid4()),
                },
                json=payload,
            )

        responses = await asyncio.gather(book(first_token), book(second_token))
        statuses = sorted(response.status_code for response in responses)
        cancelled = 0
        for response, token in zip(
            responses, (first_token, second_token), strict=True
        ):
            if response.status_code != 201:
                continue
            appointment_id = response.json()["id"]
            cancellation = await client.post(
                f"/appointments/{appointment_id}/cancel",
                headers=_headers(token),
                json={"reason": "Production concurrency check cleanup"},
            )
            cancellation.raise_for_status()
            cancelled += 1

        print(json.dumps({"statuses": statuses, "bookings_cancelled": cancelled}))
        if statuses != [201, 409]:
            raise SystemExit("Expected exactly one booking and one conflict")


if __name__ == "__main__":
    asyncio.run(main())

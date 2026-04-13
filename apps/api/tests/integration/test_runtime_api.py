from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_full_phase_one_runtime_path_via_api() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        bootstrap_response = await client.post("/registry/bootstrap")
        assert bootstrap_response.status_code == 200
        bootstrap_payload = bootstrap_response.json()
        assert bootstrap_payload["workflows"] == 3

        compile_response = await client.post("/workflows/default-bugfix/compile")
        assert compile_response.status_code == 201

        compile_payload = compile_response.json()
        assert len(compile_payload["nodes"]) == 4

        start_response = await client.post(
            "/runs/from-workflow/default-bugfix",
            json={
                "task": {
                    "title": "kernel api run",
                    "description": "phase one api run",
                    "input_payload": {"source": "test"},
                },
                "attempt_number": 1,
            },
        )
        assert start_response.status_code == 201
        start_payload = start_response.json()

        run_id = start_payload["run_id"]
        flow_id = start_payload["flow_id"]
        first_flow_node_id = start_payload["first_flow_node_id"]
        assert run_id is not None
        assert flow_id is not None

        inspect_response = await client.get(f"/runs/{run_id}")
        assert inspect_response.status_code == 200
        inspect_payload = inspect_response.json()
        assert inspect_payload["status"] == "running"
        assert inspect_payload["current_attempt_number"] == 1
        assert inspect_payload["node_count"] >= 4

        checkpoint_response = await client.post(
            "/runs/checkpoints",
            json={
                "flow_id": flow_id,
                "flow_node_id": first_flow_node_id,
                "sequence_no": 1,
                "status": "green",
                "summary": "first node executed",
                "payload": {"result": "ok"},
            },
        )
        assert checkpoint_response.status_code == 201
        checkpoint_payload = checkpoint_response.json()
        assert checkpoint_payload["status"] == "green"
        assert checkpoint_payload["summary"] == "first node executed"

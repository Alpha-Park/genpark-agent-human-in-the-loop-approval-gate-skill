import sys, json
from client import AgentHumanInTheLoopApprovalGate

def handle_mcp():
    gate = AgentHumanInTheLoopApprovalGate()
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print(json.dumps(gate.run_benchmark_approval_gate(), indent=2))
        return

    for line in sys.stdin:
        if not line.strip(): continue
        try:
            try:
                req = json.loads(line)
            except json.JSONDecodeError as exc:
                print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}), flush=True)
                continue
            if not isinstance(req, dict) or req.get("jsonrpc") != "2.0" or not isinstance(req.get("method"), str):
                print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request"}}), flush=True)
                continue
            # JSON-RPC notifications never receive a response or execute request-only tools.
            if "id" not in req:
                continue
            if req["method"] == "initialize":
                print(json.dumps({"jsonrpc": "2.0", "id": req["id"], "result": {
                    "protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                    "serverInfo": {"name": 'genpark-agent-human-in-the-loop-approval-gate-skill', "version": "1.0.0"}
                }}), flush=True)
                continue
            if req["method"] == "ping":
                print(json.dumps({"jsonrpc": "2.0", "id": req["id"], "result": {}}), flush=True)
                continue
            if req["method"] not in ("tools/list", "tools/call"):
                print(json.dumps({"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32601, "message": "Method not found"}}), flush=True)
                continue
            if req["method"] == "tools/call":
                params = req.get("params")
                if not isinstance(params, dict) or not isinstance(params.get("arguments", {}), dict) or params.get("name") not in ('evaluate_action_risk_tier', 'create_reversible_checkpoint', 'issue_approval_token', 'run_benchmark_approval_gate'):
                    print(json.dumps({"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32602, "message": "Unknown tool or invalid arguments"}}), flush=True)
                    continue
            method = req.get("method")
            msg_id = req.get("id")
            
            if method == "tools/list":
                resp = {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": [
                    {"name": "evaluate_action_risk_tier", "description": "Classify action risk and determine approval requirements.", "inputSchema": {"type": "object", "properties": {"action_command": {"type": "string"}, "estimated_impact_usd": {"type": "number"}}}},
                    {"name": "create_reversible_checkpoint", "description": "Create rollback snapshot before mutating actions.", "inputSchema": {"type": "object", "properties": {"state_snapshot": {"type": "object"}}}},
                    {"name": "issue_approval_token", "description": "Generate cryptographically verifiable one-time execution token.", "inputSchema": {"type": "object", "properties": {"action_id": {"type": "string"}}}},
                    {"name": "run_benchmark_approval_gate", "description": "Run human-in-the-loop safety gate benchmark.", "inputSchema": {"type": "object"}}
                ]}}
            elif method == "tools/call":
                tname = req.get("params", {}).get("name")
                args = req.get("params", {}).get("arguments", {})
                if tname == "evaluate_action_risk_tier":
                    res = gate.evaluate_action_risk_tier(args.get("action_command", ""), args.get("estimated_impact_usd", 0.0))
                elif tname == "create_reversible_checkpoint":
                    res = gate.create_reversible_checkpoint(args.get("state_snapshot", {}))
                elif tname == "issue_approval_token":
                    res = gate.issue_approval_token(args.get("action_id", ""), args.get("user_approved", True))
                else:
                    res = gate.run_benchmark_approval_gate()
                resp = {"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}}
            else:
                resp = {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": "Method not found"}}
            
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": req.get("id") if isinstance(req, dict) else None, "error": {"code": -32000, "message": str(e)}}) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    handle_mcp()

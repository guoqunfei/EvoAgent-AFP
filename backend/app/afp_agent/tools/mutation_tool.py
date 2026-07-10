"""
序列突变工具 - 精准操控氨基酸序列突变（AFP版）
注册为: mutate_sequence
"""

from app.afp_agent.tools.registry import registry


def mutate_sequence_handler(args: dict) -> dict:
    sequence = args.get("original_sequence", args.get("sequence", "")).upper()
    mutations = args.get("mutations", [])
    description = args.get("description", "")

    if not sequence:
        return {"error": "请提供原始序列"}
    if not mutations:
        return {"error": "请提供至少一个突变"}

    mutated = list(sequence)
    mutation_log = []

    for mut in mutations:
        pos = mut.get("position", -1)
        from_aa = mut.get("from", "")
        to_aa = mut.get("to", "")

        if pos < 0 or pos >= len(sequence):
            mutation_log.append({"position": pos, "status": "invalid", "error": f"位置{pos}超出序列范围"})
            continue

        actual_aa = sequence[pos]
        if from_aa and actual_aa != from_aa:
            mutation_log.append({"position": pos, "status": "warning", "expected": from_aa, "actual": actual_aa, "target": to_aa})

        if to_aa not in "ACDEFGHIKLMNPQRSTVWY":
            mutation_log.append({"position": pos, "status": "error", "error": f"无效的目标氨基酸: {to_aa}"})
            continue

        old_aa = mutated[pos]
        mutated[pos] = to_aa
        mutation_log.append({"position": pos, "status": "success", "from": old_aa, "to": to_aa})

    mutated_sequence = "".join(mutated)
    mutation_count = sum(1 for m in mutation_log if m["status"] == "success")

    return {
        "original_sequence": sequence, "mutated_sequence": mutated_sequence,
        "sequence_length": len(sequence), "mutation_count": mutation_count,
        "mutation_log": mutation_log, "description": description,
    }


registry.register(
    name="mutate_sequence", toolset="afp",
    schema={
        "type": "function",
        "function": {
            "name": "mutate_sequence",
            "description": "在抗冻蛋白序列的指定位置执行精确的氨基酸突变，用于改造冰结合面残基或优化蛋白骨架",
            "parameters": {
                "type": "object",
                "properties": {
                    "sequence": {"type": "string", "description": "原始氨基酸序列"},
                    "mutations": {
                        "type": "array", "description": "突变列表",
                        "items": {"type": "object", "properties": {
                            "position": {"type": "integer"}, "from": {"type": "string"}, "to": {"type": "string"}
                        }, "required": ["position", "to"]}
                    },
                    "description": {"type": "string", "description": "突变描述和理由"}
                },
                "required": ["sequence", "mutations"]
            }
        }
    },
    handler=lambda args, **kw: mutate_sequence_handler(args),
    description="精准操控抗冻蛋白氨基酸序列突变",
    emoji="🧬"
)

# -*- coding: utf-8 -*-
"""harness 测试运行器：校验 cases/*.json 结构完整性，并对 boundary 用例做可执行断言。
用法：python run_cases.py            # 校验全部用例结构
     python run_cases.py --exec     # 附加执行 boundary 用例的脚本断言（需要数据目录）
"""
import glob, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
REQUIRED_KEYS = ['case_id', 'name', 'type', 'user_input', 'expected']
VALID_TYPES = {'trigger', 'boundary', 'expect-no-trigger'}

def main():
    exec_mode = '--exec' in sys.argv
    results = []
    for f in sorted(glob.glob(os.path.join(HERE, 'cases', '*.json'))):
        case = json.load(open(f, encoding='utf-8'))
        errs = []
        for k in REQUIRED_KEYS:
            if k not in case:
                errs.append(f'缺少字段 {k}')
        if case.get('type') not in VALID_TYPES:
            errs.append(f'type 非法：{case.get("type")}')
        if case.get('type') == 'trigger' and case['expected'].get('skill_triggered') is not True:
            errs.append('trigger 用例 expected.skill_triggered 必须为 true')
        if case.get('type') == 'expect-no-trigger' and case['expected'].get('skill_triggered') is not False:
            errs.append('expect-no-trigger 用例 expected.skill_triggered 必须为 false')
        results.append({'case': case.get('case_id', f), 'struct_ok': not errs, 'errors': errs})

        if exec_mode and case.get('case_id') == '02-missing-input':
            # 可执行断言：指向一个不存在的目录，validate_inputs 必须退出码 2 且输出 JSON 错误
            r = subprocess.run([sys.executable, os.path.join(SKILL, 'scripts', 'validate_inputs.py'),
                                '--data-dir', r'C:\nonexistent_dir_for_test'],
                               capture_output=True, text=True)
            out = json.loads(r.stdout)
            ok = r.returncode == 2 and out.get('ok') is False and out.get('errors')
            results.append({'case': '02-missing-input (exec)', 'struct_ok': bool(ok),
                            'errors': [] if ok else [f'退出码={r.returncode}, stdout={r.stdout[:200]}']})

    all_ok = all(r['struct_ok'] for r in results)
    print(json.dumps({'ok': all_ok, 'results': results}, ensure_ascii=False, indent=1))
    sys.exit(0 if all_ok else 1)

if __name__ == '__main__':
    main()

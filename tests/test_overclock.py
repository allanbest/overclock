import json
import os
import py_compile
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_PY = os.path.join(REPO, "skills", "deepwork", "scripts", "project.py")
SESSION_START = os.path.join(REPO, "hooks", "session_start.py")
PRE_COMPACT = os.path.join(REPO, "hooks", "pre_compact.py")


def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_py(script, args=None, stdin_data=None, cwd=None, env_overrides=None):
    env = os.environ.copy()
    for k in ("OVERCLOCK_OFF", "OVERCLOCK_RULES", "OVERCLOCK_RESUME",
              "OVERCLOCK_CHECKPOINT", "OVERCLOCK_DEEPWORK"):
        env.pop(k, None)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [sys.executable, script] + (args or []),
        input=stdin_data,
        text=True,
        capture_output=True,
        cwd=cwd or REPO,
        env=env,
    )


class TestProjectCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = os.path.join(self.tmp.name, "repo")
        os.makedirs(os.path.join(self.ws, ".git"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_init_all_modes_and_gitignore(self):
        for slug, mode, expected_files in [
            ("sci-proj", "science", ("brief.md", "state.md", "decisions.md", "lab.md")),
            ("bld-proj", "build", ("brief.md", "state.md", "decisions.md", "spec.md", "tasks.md")),
            ("res-proj", "research", ("brief.md", "state.md", "decisions.md", "plan.md")),
        ]:
            res = run_py(PROJECT_PY, [
                "init", slug, "--mode", mode, "--goal", f"Goal for {slug}",
                "--cwd", self.ws, "--gitignore",
            ])
            self.assertEqual(res.returncode, 0, res.stderr)
            pdir = os.path.join(self.ws, ".overclock", "projects", slug)
            for fname in expected_files:
                self.assertTrue(os.path.isfile(os.path.join(pdir, fname)), f"Missing {fname}")
            chk = run_py(PROJECT_PY, ["check-state", "--cwd", self.ws])
            self.assertEqual(chk.returncode, 0, chk.stderr)

        gi = read_text(os.path.join(self.ws, ".gitignore"))
        self.assertEqual(gi.splitlines().count(".overclock/"), 1)

    def test_status_switch_stop_resume_and_subdir_walkup(self):
        res = run_py(PROJECT_PY, [
            "init", "alpha", "--mode", "research", "--goal", "Survey benchmarks", "--cwd", self.ws
        ])
        self.assertEqual(res.returncode, 0, res.stderr)

        sub = os.path.join(self.ws, "src", "nested")
        os.makedirs(sub)
        st = run_py(PROJECT_PY, ["status", "--cwd", sub, "--json"])
        self.assertEqual(st.returncode, 0, st.stderr)
        data = json.loads(st.stdout)
        self.assertEqual(data["active"], "alpha")
        self.assertEqual(data["active_project"]["mode"], "research")

        sw = run_py(PROJECT_PY, ["switch-mode", "build", "--cwd", sub])
        self.assertEqual(sw.returncode, 0, sw.stderr)
        pdir = os.path.join(self.ws, ".overclock", "projects", "alpha")
        self.assertTrue(os.path.isfile(os.path.join(pdir, "plan.md")))
        self.assertTrue(os.path.isfile(os.path.join(pdir, "spec.md")))
        self.assertTrue(os.path.isfile(os.path.join(pdir, "tasks.md")))
        self.assertIn("mode-switch", read_text(os.path.join(pdir, "decisions.md")))

        stop = run_py(PROJECT_PY, ["stop", "--pause", "--cwd", sub])
        self.assertEqual(stop.returncode, 0, stop.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.ws, ".overclock", "active")))
        self.assertIn("Status: paused", read_text(os.path.join(pdir, "state.md")))

        resm = run_py(PROJECT_PY, ["resume", "alpha", "--cwd", sub])
        self.assertEqual(resm.returncode, 0, resm.stderr)
        self.assertTrue(os.path.isfile(os.path.join(self.ws, ".overclock", "active")))
        self.assertIn("Status: active", read_text(os.path.join(pdir, "state.md")))

    def test_check_state_budget_enforcement(self):
        run_py(PROJECT_PY, ["init", "budget", "--mode", "science", "--goal", "Test", "--cwd", self.ws])
        state_path = os.path.join(self.ws, ".overclock", "projects", "budget", "state.md")
        with open(state_path, "a", encoding="utf-8") as f:
            for i in range(35):
                f.write(f"Extra line {i}\n")
        chk = run_py(PROJECT_PY, ["check-state", "--cwd", self.ws])
        self.assertEqual(chk.returncode, 1)
        self.assertIn("too many lines", chk.stderr)


class TestHooks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = os.path.join(self.tmp.name, "ws")
        os.makedirs(os.path.join(self.ws, ".git"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_antigravity_silent_when_inactive(self):
        payload = json.dumps({
            "conversationId": "c1",
            "workspacePaths": [self.ws],
            "cwd": self.ws,
            "hookEventName": "SessionStart",
        })
        res = run_py(SESSION_START, stdin_data=payload)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(json.loads(res.stdout), {})

    def test_antigravity_active_nested_stop_and_off(self):
        run_py(PROJECT_PY, ["init", "ml-exp", "--mode", "science", "--goal", "Tune loss", "--cwd", self.ws])
        sub = os.path.join(self.ws, "sub", "dir")
        os.makedirs(sub)
        payload = json.dumps({
            "conversationId": "c2",
            "workspacePaths": [self.ws],
            "cwd": sub,
            "hookEventName": "SessionStart",
        })
        res = run_py(SESSION_START, stdin_data=payload)
        self.assertEqual(res.returncode, 0, res.stderr)
        out = json.loads(res.stdout)
        msg = out["injectSteps"][0]["systemMessage"]["systemMessage"]
        self.assertIn("ml-exp", msg)
        self.assertIn("mode-science.md", msg)
        self.assertNotIn("overclock efficiency rules", msg)

        # OVERCLOCK_DEEPWORK=off silences it
        off = run_py(SESSION_START, stdin_data=payload, env_overrides={"OVERCLOCK_DEEPWORK": "off"})
        self.assertEqual(json.loads(off.stdout), {})

        # Stop silences it
        run_py(PROJECT_PY, ["stop", "--complete", "--cwd", self.ws])
        stopped = run_py(SESSION_START, stdin_data=payload)
        self.assertEqual(json.loads(stopped.stdout), {})

    def test_antigravity_state_truncation(self):
        run_py(PROJECT_PY, ["init", "big", "--mode", "build", "--goal", "Big state", "--cwd", self.ws])
        st = os.path.join(self.ws, ".overclock", "projects", "big", "state.md")
        with open(st, "a", encoding="utf-8") as f:
            f.write(("Line with details.\n") * 200)
        payload = json.dumps({"conversationId": "c3", "cwd": self.ws, "hookEventName": "SessionStart"})
        res = run_py(SESSION_START, stdin_data=payload)
        msg = json.loads(res.stdout)["injectSteps"][0]["systemMessage"]["systemMessage"]
        self.assertIn("full state in", msg)
        self.assertLess(len(msg), 3000)

    def test_claude_session_start_modes(self):
        # Inactive: RULES only
        res0 = run_py(SESSION_START, stdin_data=json.dumps({"session_id": "s1", "source": "startup", "cwd": self.ws}))
        ctx0 = json.loads(res0.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("overclock efficiency rules", ctx0)
        self.assertNotIn("Deepwork project", ctx0)

        # Active: startup/clear/compact include project; resume skips project
        run_py(PROJECT_PY, ["init", "app1", "--mode", "build", "--goal", "Build CLI", "--cwd", self.ws])
        for src in ("startup", "clear", "compact"):
            r = run_py(SESSION_START, stdin_data=json.dumps({"session_id": "s2", "source": src, "cwd": self.ws}))
            c = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
            self.assertIn("app1", c)
            self.assertLess(len(c), 9000)

        r_res = run_py(SESSION_START, stdin_data=json.dumps({"session_id": "s2", "source": "resume", "cwd": self.ws}))
        c_res = json.loads(r_res.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("overclock efficiency rules", c_res)
        self.assertNotIn("app1", c_res)

        r_norules = run_py(
            SESSION_START,
            stdin_data=json.dumps({"session_id": "s2", "source": "startup", "cwd": self.ws}),
            env_overrides={"OVERCLOCK_RULES": "off"},
        )
        c_nr = json.loads(r_norules.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("overclock efficiency rules", c_nr)
        self.assertIn("app1", c_nr)

    def test_pre_compact_active_vs_inactive(self):
        r0 = run_py(PRE_COMPACT, stdin_data=json.dumps({"cwd": self.ws}))
        self.assertEqual(r0.returncode, 0)
        self.assertIn("When summarizing, keep:", r0.stdout)
        self.assertNotIn("Deepwork project", r0.stdout)

        run_py(PROJECT_PY, ["init", "phy", "--mode", "science", "--goal", "Check conservation", "--cwd", self.ws])
        r1 = run_py(PRE_COMPACT, stdin_data=json.dumps({"cwd": self.ws}))
        self.assertIn("phy", r1.stdout)
        self.assertIn("dead ends", r1.stdout.lower())

    def test_existing_hooks_regression(self):
        for rel in ("compress_output.py", "checkpoint.py", "idle_check.py"):
            path = os.path.join(REPO, "hooks", rel)
            py_compile.compile(path, doraise=True)
            res = run_py(path, stdin_data=json.dumps({"cwd": self.ws}))
            self.assertEqual(res.returncode, 0, f"{rel} failed: {res.stderr}")


class TestSchemas(unittest.TestCase):
    def test_manifests_and_hooks_schemas(self):
        root_pj = read_json(os.path.join(REPO, "plugin.json"))
        allowed_ag_keys = {
            "name", "displayName", "version", "description", "logo",
            "suggestedPrompts", "author", "homepage", "repository", "disabled",
        }
        self.assertTrue(set(root_pj.keys()).issubset(allowed_ag_keys))
        self.assertEqual(root_pj["name"], "overclock")
        self.assertEqual(root_pj["version"], "1.0.0")
        self.assertTrue(os.path.isfile(os.path.join(REPO, root_pj["logo"])))

        root_hooks = read_json(os.path.join(REPO, "hooks.json"))
        ss = root_hooks["overclock-project-resume"]["SessionStart"]
        self.assertIsInstance(ss, list)
        self.assertEqual(ss[0]["type"], "command")

        claude_pj = read_json(os.path.join(REPO, ".claude-plugin", "plugin.json"))
        self.assertEqual(claude_pj["version"], "1.0.0")
        self.assertEqual(claude_pj["agents"], ["./claude-agents/scout.md", "./claude-agents/worker.md"])
        self.assertFalse(os.path.exists(os.path.join(REPO, "agents")))
        self.assertTrue(os.path.isfile(os.path.join(REPO, "claude-agents", "scout.md")))
        self.assertTrue(os.path.isfile(os.path.join(REPO, "claude-agents", "worker.md")))

        mkt = read_json(os.path.join(REPO, ".claude-plugin", "marketplace.json"))
        self.assertEqual(mkt["plugins"][0]["version"], "1.0.0")

        claude_hooks = read_json(os.path.join(REPO, "hooks", "hooks.json"))
        self.assertIn("SessionStart", claude_hooks["hooks"])
        self.assertIn("PostToolUse", claude_hooks["hooks"])

    def test_skills_frontmatter_and_references(self):
        skills_dir = os.path.join(REPO, "skills")
        expected = {"deepwork", "orchestrate", "reflect", "stop", "handoff"}
        self.assertEqual(set(os.listdir(skills_dir)), expected)
        for name in expected:
            skill_md = os.path.join(skills_dir, name, "SKILL.md")
            text = read_text(skill_md)
            self.assertTrue(text.startswith("---\n"), f"{skill_md} missing frontmatter")
            fm = text.split("---\n", 2)[1]
            self.assertIn(f"name: {name}", fm)
            self.assertIn("description:", fm)
        for ref in ("mode-science.md", "mode-build.md", "mode-research.md", "verification.md"):
            self.assertTrue(os.path.isfile(os.path.join(skills_dir, "deepwork", "references", ref)))
        self.assertTrue(os.path.isfile(PROJECT_PY))


if __name__ == "__main__":
    unittest.main()

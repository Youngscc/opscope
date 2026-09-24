"""用真实的本地 Git 仓库验证分支同步，不连接托管服务。"""

import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("sync_gitcode_branch.sh")


class BranchSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.target = self.root / "target.git"
        self.git(self.root, "init", "-b", "main", str(self.source))
        self.git(self.root, "init", "--bare", str(self.target))
        self.git(self.source, "config", "user.name", "Sync Test")
        self.git(self.source, "config", "user.email", "sync@example.invalid")
        self.commit("initial")
        self.branch = "codex/opscope-modeling-integration"

    def git(self, directory, *args):
        return subprocess.check_output(
            ["git", "-C", str(directory), *args], stderr=subprocess.DEVNULL,
        ).decode().strip()

    def commit(self, message):
        self.git(self.source, "commit", "--allow-empty", "-m", message)
        return self.git(self.source, "rev-parse", "HEAD")

    def sync(self, dry_run="false"):
        return subprocess.run(
            ["bash", str(SCRIPT), str(self.target), self.branch, dry_run],
            cwd=self.source, capture_output=True, text=True,
        )

    def target_sha(self):
        return self.git(self.target, "rev-parse", "refs/heads/" + self.branch)

    def test_create_and_fast_forward_preserve_commit_identity(self):
        # 新建、重复同步及快进均指向同一提交对象，作者/历史无需重建。
        self.assertEqual(self.sync().returncode, 0)
        self.assertEqual(self.sync().returncode, 0)
        expected = self.commit("second")
        self.assertEqual(self.sync().returncode, 0)
        self.assertEqual(self.target_sha(), expected)
        self.assertEqual(self.git(self.target, "rev-list", "--count", expected), "2")

    def test_other_branches_and_tags_are_untouched(self):
        # 即使本地配置跟随标签，也只能更新指定分支，不能修改 main 或复制标签。
        original = self.git(self.source, "rev-parse", "HEAD")
        self.git(self.source, "push", str(self.target), "HEAD:main")
        self.commit("development")
        self.git(self.source, "tag", "-a", "v-test", "-m", "tag")
        self.git(self.source, "config", "push.followTags", "true")
        self.assertEqual(self.sync().returncode, 0)
        self.assertEqual(self.git(self.target, "rev-parse", "main"), original)
        self.assertEqual(self.git(self.target, "tag", "--list"), "")

    def test_divergent_target_is_preserved(self):
        # 目标独立提交后，源从共同祖先继续开发；同步必须失败并保留目标 SHA。
        base = self.git(self.source, "rev-parse", "HEAD")
        remote_commit = self.commit("target only")
        self.git(self.source, "push", str(self.target), "HEAD:refs/heads/" + self.branch)
        self.git(self.source, "checkout", "--detach", base)
        self.commit("source only")
        result = self.sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to overwrite", result.stderr)
        self.assertEqual(self.target_sha(), remote_commit)

    def test_dry_run_does_not_create_a_branch(self):
        # 首次演练可以校验推送，但目标仓库不能产生任何引用。
        self.assertEqual(self.sync("true").returncode, 0)
        self.assertEqual(self.git(self.target, "for-each-ref"), "")

    def test_invalid_branch_is_rejected(self):
        # 防止错误分支参数变成额外 refspec 或选项。
        self.branch = "main:other"
        self.assertNotEqual(self.sync().returncode, 0)
        self.assertEqual(self.git(self.target, "for-each-ref"), "")


if __name__ == "__main__":
    unittest.main()

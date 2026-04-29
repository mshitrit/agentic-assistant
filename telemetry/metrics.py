from dataclasses import dataclass


@dataclass
class SlackMetrics:
    threads_started: int = 0
    followups: int = 0
    success: int = 0
    errors: int = 0

    def _print(self):
        print(
            f"[TELEMETRY] Slack | "
            f"threads_started={self.threads_started}  "
            f"followups={self.followups}  "
            f"success={self.success}  "
            f"errors={self.errors}"
        )

    def inc_threads_started(self):
        self.threads_started += 1
        self._print()

    def inc_followups(self):
        self.followups += 1
        self._print()

    def inc_success(self):
        self.success += 1
        self._print()

    def inc_errors(self):
        self.errors += 1
        self._print()


@dataclass
class JiraMetrics:
    analyses_posted: int = 0
    errors: int = 0

    def _print(self):
        print(
            f"[TELEMETRY] Jira  | "
            f"analyses_posted={self.analyses_posted}  "
            f"errors={self.errors}"
        )

    def inc_analyses_posted(self):
        self.analyses_posted += 1
        self._print()

    def inc_errors(self):
        self.errors += 1
        self._print()


slack_metrics = SlackMetrics()
jira_metrics  = JiraMetrics()

# skill-demo-sandbox

A public sandbox repo for the **Hands-Free Claude** YouTube series by
[Amplify Imagination](https://youtube.com/@AmplifyImagination).

## What this is

A tiny project (Hello-World-grade) with real GitHub Actions CI, used as a
test bed for the **Claude Skills** demonstrated in the series. Real builds,
real failures, real recovery — so the on-screen demos are auditable.

Fork this repo, install the skills under skills/, and watch them work.

## What's in here

- app/hello.py - trivial function (greet(name) -> str)
- tests/test_hello.py - pytest tests for it
- pyproject.toml - ruff + pytest config
- .github/workflows/ci.yml - lint + test on every push
- skills/watch-ci/SKILL.md - the skill demonstrated in EP01

## Episode index

- EP01 - Loop Any Claude Skill | skills/watch-ci/
- EP02 - Audit Your Skills | skills/skill-audit/ (coming)

## License

MIT. Fork freely, learn freely.

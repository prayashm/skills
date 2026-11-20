# skills

Agent skills I use day to day, in the [Agent Skills](https://agentskills.io) format
(`SKILL.md` plus scripts). They work with Claude Code and other agents that read skills.

| Skill                          | What it does                                                        |
| ------------------------------ | ------------------------------------------------------------------- |
| [yesno-label](yesno-label/)    | One-card-at-a-time yes/no or A/B video labelling page, saved as JSONL |

## Install

Copy or symlink a skill folder into your agent's skills directory, for example:

```bash
git clone https://github.com/prayashm/skills.git
ln -s "$PWD/skills/yesno-label" ~/.claude/skills/yesno-label
```

Each script can also run on its own: `python3 yesno-label/scripts/yesno.py --help`.

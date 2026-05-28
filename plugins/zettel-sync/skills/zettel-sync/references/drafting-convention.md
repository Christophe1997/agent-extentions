# Drafting convention

How to draft a seed note or MOC that matches this vault. **Read
`_templates/_schema.md` from the vault first** — it is the source of truth for
frontmatter; the rules below are the stable parts plus the house style observed
in existing notes.

## Principles

- **Seed, not essay.** A new note captures *what the session explored* —
  frontmatter, a thesis line, the sub-points actually discussed, and links. The
  user writes the real synthesis during promotion. Don't fabricate depth the
  session didn't reach.
- **Chinese prose.** Title and body are Chinese. **Tags stay lowercase-English
  kebab-case** (`distributed-systems`, `go`, `consensus`). Code, commands, and
  established technical terms keep their original form.
- **Everything lands in `inbox/`.** Never write to `notes/` or `moc/`.

## Frontmatter (from the schema)

Required on every note: `type`, `created`, `updated`, `tags`.
- `type: note` for seed notes; `type: moc` for MOC drafts.
- `created` and `updated` = today (`YYYY-MM-DD`), identical on a new draft.
- `tags`: 2–4 lowercase-English topic tags. Reuse existing vault tags where they
  fit (the analyzer reports each note's tags; or check `notes/` via the MCP) so
  the note clusters correctly.

## Filename = wikilink target

The filename stem is how other notes will `[[link]]` to it. Match existing
style: kebab-case for Latin titles (`raft-consensus.md`), the raw term for CJK
titles (`分布式锁.md`). Keep it short and stable.

## Seed note shape

```markdown
---
type: note
created: 2026-05-28
updated: 2026-05-28
tags: [distributed-systems, consensus]
---
# Raft 共识算法

> Raft 把共识拆成「Leader 选举 + 日志复制 + 安全性约束」三块,用可理解性换 Paxos 的理论简洁 —— 草拟提要,请按你的理解重写。

---

## 提纲(本次会话涉及)
- Leader 选举:随机化超时、任期(term)单调递增、多数票当选
- 日志复制:AppendEntries 一致性检查、commitIndex 推进
- 安全性:选举限制(只投给日志不旧于自己的候选人)、日志匹配性质

## 相关
- [[分布式锁]] — 协作型互斥与强一致共识的边界
- [[Linux Internals MOC]]

## Reference
- (会话来源 / 论文 / 链接)
```

Notes on the shape:
- The `> 提要` is a **draft** one-liner distilled from the session, explicitly
  inviting the user to rewrite it. The note living in `inbox/` already signals
  "undigested."
- The outline lists only sub-points the session actually covered.
- **Only link to stems that exist** in the vault (the analyzer reports the note
  inventory; `obsidian_list_files_in_dir` lists `notes/`/`moc/`). Proposing a
  link to a not-yet-existing note is fine *only* if you're also proposing that
  note in the same run — otherwise it's a dead link. Header links
  (`[[note#Heading]]`) are allowed when you know the target heading exists.

## MOC draft shape

Triggered when ≥5 notes share a tag with no MOC. Title is Title Case + ` MOC`;
the draft is curated, not a dump (the vault's MOCs say *"a note earns a link
when I'd send a friend there first"*).

```markdown
---
type: moc
created: 2026-05-28
updated: 2026-05-28
tags: [distributed-systems]
---
# Distributed Systems MOC

> 分布式系统的工作地图 —— 从一致性原语到协调服务。**策展,非清单。**

---

## 一致性与共识
- [[raft-consensus]] — 可理解的共识算法,从这里开始。

## 协调与锁
- [[分布式锁]] — 四种互斥原语,按 fencing 需求选型。

## Open questions
- *(待写)* —— 标记尚未成文的线索,成文后替换为 [[link]]。

---
*Last curated: 2026-05-28*
```

Cluster the member notes under 2–4 themed sections; leave `*(待写)*` bullets for
gaps. Do not invent notes that don't exist.

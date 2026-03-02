---
name: Redis Messaging Patterns
description: Use when the user asks about queues, message queues, job queues, reliable delivery, delayed tasks, scheduled jobs, event streaming, consumer groups, pub/sub, notifications, or message processing with Redis. Triggers on queries like "how to implement a queue", "reliable messaging", "Redis streams", "delayed execution".
version: 1.0.0
---

# Redis Messaging Patterns

## ⚡ Code Example Guidelines

When showing code examples:
1. **Detect the project's programming language** first (check package.json, go.mod, requirements.txt, pom.xml, etc.)
2. **Generate code in the detected language** using the appropriate Redis client
3. **If no language detected**, use pseudocode with Redis commands as shown below

Solutions for messaging, queuing, and event streaming use cases.

## Use Case → Pattern Mapping

| Use Case | Recommended Pattern |
|----------|---------------------|
| Simple FIFO queue | List-based Queue (LPUSH/RPOP) |
| Reliable message delivery | Reliable Queue (LMOVE) |
| Delayed/scheduled tasks | Delayed Queue (Sorted Set) |
| Multiple consumers, message persistence | Streams with Consumer Groups |
| Fire-and-forget notifications | Pub/Sub |

---

## Pattern 1: Simple FIFO Queue

**When to use:** Basic queue where occasional message loss is acceptable.

### Redis Commands
```bash
LPUSH queue:tasks {task_data}    # Add to front of queue
RPOP queue:tasks                  # Remove from back of queue
LLEN queue:tasks                  # Get queue length
```

### Pseudocode
```
# Producer
function enqueue(task):
    REDIS.LPUSH("queue:tasks", serialize(task))

# Consumer
function dequeue():
    task = REDIS.RPOP("queue:tasks")
    IF task:
        RETURN parse(task)
    RETURN NULL
```

**Pros:** Simple, fast
**Cons:** Message lost if consumer crashes after RPOP

---

## Pattern 2: Reliable Queue

**When to use:** When at-least-once delivery guarantee is required.

**How it works:** Use LMOVE to atomically transfer messages to a processing list, enabling recovery if consumers crash.

### Redis Commands
```bash
LMOVE queue:tasks queue:processing RIGHT LEFT   # Atomically move to processing
LREM queue:processing 1 {task_data}              # Remove after successful processing
LRANGE queue:processing 0 -1                     # Get all processing tasks (for recovery)
```

### Pseudocode
```
# Consumer with reliability
function process_task():
    # Atomically move from pending to processing
    task = REDIS.LMOVE("queue:tasks", "queue:processing", "RIGHT", "LEFT")

    IF task:
        TRY:
            data = parse(task)
            do_work(data)
            # Remove from processing queue on success
            REDIS.LREM("queue:processing", 1, task)
        CATCH error:
            # Task remains in processing queue for recovery
            log_error(error)

# Recovery: re-queue stuck tasks
function recover_stuck_tasks(timeout=300):
    now = current_time()
    tasks = REDIS.LRANGE("queue:processing", 0, -1)

    FOR task IN tasks:
        data = parse(task)
        IF now - data.started_at > timeout:
            REDIS.LMOVE("queue:processing", "queue:tasks", "RIGHT", "LEFT")
```

**Pros:** At-least-once delivery, crash recovery
**Cons:** Slightly more complex, idempotent processing needed

---

## Pattern 3: Delayed Queue

**When to use:** Schedule tasks for future execution.

**How it works:** Use a Sorted Set where the score is the Unix timestamp when the task should run.

### Redis Commands
```bash
ZADD queue:delayed {timestamp} {task_data}      # Schedule task
ZRANGEBYSCORE queue:delayed 0 {now}             # Get ready tasks
ZREM queue:delayed {task_data}                  # Remove after processing
```

### Pseudocode
```
# Schedule a task
function schedule_task(task, delay_seconds):
    execute_at = current_timestamp() + delay_seconds
    REDIS.ZADD("queue:delayed", execute_at, serialize(task))

# Worker to process delayed tasks
function process_delayed():
    now = current_timestamp()

    # Get tasks ready to execute
    ready = REDIS.ZRANGEBYSCORE("queue:delayed", 0, now)

    FOR task_json IN ready:
        # Remove from delayed queue (atomic check)
        IF REDIS.ZREM("queue:delayed", task_json):
            task = parse(task_json)
            # Move to active queue or process directly
            REDIS.LPUSH("queue:tasks", task_json)

# Run worker periodically
LOOP:
    process_delayed()
    SLEEP(1)
```

**Pros:** Precise scheduling, efficient time-based queries
**Cons:** Polling required (or use keyspace notifications)

---

## Pattern 4: Redis Streams with Consumer Groups

**When to use:** Multiple consumers, message persistence, acknowledgment, and historical replay.

**How it works:** Streams provide a persistent, append-only log with consumer group support.

### Redis Commands
```bash
# Producer
XADD mystream * field1 value1 field2 value2

# Consumer Group Setup
XGROUP CREATE mystream mygroup $ MKSTREAM

# Consumer
XREADGROUP GROUP mygroup consumer1 COUNT 10 BLOCK 5000 STREAMS mystream >
XACK mystream mygroup {message_id}

# Recovery
XPENDING mystream mygroup - + 10 {min_idle_time}
XCLAIM mystream mygroup consumer1 {min_idle_time} {message_id}

# Memory Management
XTRIM mystream MAXLEN 10000
```

### Pseudocode
```
# Producer
function publish_event(stream, event):
    RETURN REDIS.XADD(stream, "*", event)

# Consumer with consumer group
function consume_events(stream, group, consumer):
    # Create consumer group if not exists
    TRY:
        REDIS.XGROUP_CREATE(stream, group, id="0")
    CATCH:
        PASS  # Group already exists

    LOOP:
        # Read new messages
        messages = REDIS.XREADGROUP(
            GROUP=group,
            CONSUMER=consumer,
            STREAMS={stream: ">"},
            COUNT=10,
            BLOCK=5000
        )

        FOR stream_name, entries IN messages:
            FOR message_id, data IN entries:
                TRY:
                    process_event(data)
                    # Acknowledge successful processing
                    REDIS.XACK(stream, group, message_id)
                CATCH error:
                    log_error(error)
                    # Message will be redelivered

# Claim pending messages (for crashed consumers)
function claim_abandoned(stream, group, consumer, min_idle_time=60000):
    pending = REDIS.XPENDING_RANGE(stream, group, "-", "+", 10, min_idle_time)
    FOR p IN pending:
        claimed = REDIS.XCLAIM(stream, group, consumer, min_idle_time, [p.message_id])
        # Reprocess claimed messages
```

**Pros:** Persistent, replayable, multiple consumers, exactly-once semantics possible
**Cons:** More complex, memory management needed (XTRIM)

---

## Pattern 5: Pub/Sub

**When to use:** Fire-and-forget notifications, chat, live updates where missed messages are acceptable.

### Redis Commands
```bash
PUBLISH channel:name {message}    # Publish message
SUBSCRIBE channel:name            # Subscribe to channel
PSUBSCRIBE pattern:*              # Pattern subscribe
```

### Pseudocode
```
# Publisher
function notify(channel, message):
    REDIS.PUBLISH(channel, serialize(message))

# Subscriber
function subscribe(channel):
    pubsub = REDIS.PUBSUB()
    pubsub.SUBSCRIBE(channel)

    FOR message IN pubsub.LISTEN():
        IF message.type == "message":
            data = parse(message.data)
            handle_notification(data)
```

**Pros:** Simple, real-time
**Cons:** No persistence, no acknowledgment, messages lost if no subscribers

---

## Comparison Table

| Feature | List Queue | Reliable Queue | Delayed Queue | Streams | Pub/Sub |
|---------|------------|----------------|---------------|---------|---------|
| Persistence | ✅ | ✅ | ✅ | ✅ | ❌ |
| Acknowledgment | ❌ | ✅ | ✅ | ✅ | ❌ |
| Multiple Consumers | ❌ | ❌ | ❌ | ✅ | ✅ |
| Historical Replay | ❌ | ❌ | ❌ | ✅ | ❌ |
| Delayed Delivery | ❌ | ❌ | ✅ | ❌ | ❌ |

---

## Anti-Patterns to Avoid

1. **Using RPOPLPUSH in Redis 6.2+** → Use LMOVE instead (deprecated)
2. **Unbounded Streams** → Use MAXLEN or XTRIM
3. **Pub/Sub for critical messages** → Use Streams instead
4. **No error handling in consumers** → Messages stuck in pending

## Quick Reference

```
# Simple Queue
LPUSH queue:tasks task_data
RPOP queue:tasks

# Reliable Queue
LMOVE queue:tasks queue:processing RIGHT LEFT
LREM queue:processing 1 task_data

# Delayed Queue
ZADD queue:delayed <timestamp> task_data
ZRANGEBYSCORE queue:delayed 0 <now>

# Streams
XADD stream * field value
XREADGROUP GROUP group consumer STREAMS stream >
XACK stream group message_id

# Pub/Sub
PUBLISH channel message
SUBSCRIBE channel
```

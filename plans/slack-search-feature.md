# Slack Search Feature - Implementation Plan

## Overview

Add intelligent search capability to the agentic-assistant bot, allowing users to search Slack conversation history and get AI-synthesized answers based on previous discussions.

**Target Project:** `agentic-assistant`  
**Integration:** Extend existing Slack bot  
**AI Model:** LLM API (fast model for keywords, advanced model for synthesis)

---

## Goals

- Enable users to ask questions about past Slack discussions in the current channel
- Search last 3 months of history from the channel where bot is invoked
- AI-enhanced keyword extraction for better recall
- Synthesized answers with citations to original threads
- Clean user experience with progress updates

---

## User Interface

### Command Format
```
@rhwa-ai-assist [Search] <query>
```

### Example Queries
- `@rhwa-ai-assist [Search] what was the solution to the reboot loop?`
- `@rhwa-ai-assist [Search] watchdog timeout issues`
- `@rhwa-ai-assist [Search] who mentioned FAR deployment problems?`

### Response Format
```
[2-3 paragraph synthesized answer from AI]

**Sources:**
- [Thread: "Watchdog causing reboots"](slack://link) - @slintes, Jan 15
- [Thread: "FAR timeout fix"](slack://link) - @mshitrit, Feb 3
- [Thread: "Reboot loop resolved"](slack://link) - @clobrano, Mar 10

---
ℹ️ Searched 1,847 messages from #medik8s-dev (Jan 15 - Apr 15)
```

---

## Architecture

### Two-Phase AI Flow

**Phase 1: Keyword Extraction**
- User query → Fast LLM extracts search keywords
- Expands query with synonyms, related terms, acronyms
- Returns JSON array of 5-15 keywords

**Phase 2: Answer Synthesis**
- Top-ranked threads → Advanced LLM synthesizes answer
- Cites specific messages with authors and dates
- Includes Slack links to original threads

### Data Flow

```
User Query
    ↓
Parse [Search] command from current channel
    ↓
Phase 1: AI Keyword Extraction (Fast Model)
    ↓
Fetch 3 months of messages from current channel (paginated)
    ↓
Filter by keywords + Rank by relevance
    ↓
Phase 2: AI Synthesis (Advanced Model)
    ↓
Format answer with citations
    ↓
Post to Slack in current channel
```

---

## Integration with Existing Bot Infrastructure

**Current Setup:**
- Bot uses `slack_bolt` framework with `SocketModeHandler`
- Web API client available as `client` parameter (passed to handlers)
- Existing pattern in `slack/client.py` for Slack API calls

**Example from current implementation:**
```python
# slack/client.py - existing function
def fetch_thread_messages(client, channel: str, thread_ts: str) -> list:
    result = client.conversations_replies(channel=channel, ts=thread_ts)
    return result.get("messages", [])
```

**Search feature will follow the same pattern:**
```python
# slack/search.py - new function
def fetch_channel_messages(client, channel_id: str, months: int = 3) -> list:
    """Fetch messages from channel using the same client object"""
    result = client.conversations_history(
        channel=channel_id,
        limit=200,
        oldest=calculate_oldest_timestamp(months)
    )
    return result.get("messages", [])
```

**Key Points:**
- ✅ Use existing `client` object from `slack_bolt.App` 
- ✅ Same API access pattern as current thread fetching
- ✅ No new authentication or client setup needed
- ✅ Integrate with existing `@app.event("app_mention")` handler

---

## Technical Components

### 1. Search Module (`slack/search.py`)

**Responsibilities:**
- Fetch messages from Slack API (paginated) for the current channel only
- Filter messages by keywords
- Rank by: keyword matches + recency + thread engagement + reactions
- Enrich with full thread context
- Format threads for AI consumption

**Pagination Details:**

Slack API limits `conversations.history` to 200 messages per call. To fetch 3 months:

```python
def fetch_all_messages(channel_id, months_back=3):
    """
    Fetch all messages from the last N months via pagination.
    
    Process:
    1. Calculate oldest timestamp (now - months_back)
    2. Make initial API call with limit=200
    3. If response has 'next_cursor', make another call with that cursor
    4. Repeat until no more messages or reached oldest timestamp
    5. Update progress message every 400 messages
    
    Example for active channel (30 msgs/day):
    - 3 months = ~2700 messages
    - 2700 / 200 = 14 API calls
    - Takes ~15-20 seconds total
    """
    all_messages = []
    cursor = None
    oldest = (datetime.now() - timedelta(days=months_back * 30)).timestamp()
    
    while True:
        response = slack_client.conversations_history(
            channel=channel_id,
            limit=200,
            oldest=str(oldest),
            cursor=cursor
        )
        
        messages = response['messages']
        all_messages.extend(messages)
        
        # Update progress message every 400 messages
        if len(all_messages) % 400 == 0:
            update_progress(f"📥 Fetched {len(all_messages)} messages...")
        
        if not response['has_more']:
            break
            
        cursor = response['next_cursor']
    
    return all_messages
```

**Key Methods:**
```python
class SlackSearch:
    def search(channel_id, query, options) -> List[Dict]
    def _fetch_messages(channel_id, months=3) -> List[Dict]
    def _keyword_filter(messages, keywords) -> List[Dict]
    def _enrich_threads(messages, channel_id) -> List[Dict]
    def _rank_results(messages) -> List[Dict]
    def format_thread_for_agent(message) -> str
```

**Ranking Algorithm:**
```python
score = 0
score += keyword_match_ratio * 2.0        # 0-2 points
score += exp(-days_ago / 30) * 1.0        # 0-1 points (recency)
score += min(reply_count * 0.2, 2.0)      # 0-2 points (engagement)
score += min(reaction_count * 0.1, 1.0)   # 0-1 points (reactions)
```

### 2. AI Integration (`slack/ai_search.py`)

**Phase 1: Keyword Extraction**
```python
def extract_keywords(query: str) -> List[str]:
    """
    Send query to fast LLM model to extract search keywords
    Returns: ["keyword1", "keyword2", ...]
    """
```

**Phase 2: Answer Synthesis**
```python
def synthesize_answer(query: str, threads: List[str]) -> str:
    """
    Send query + formatted threads to advanced LLM model
    Returns: Synthesized answer with citations
    """
```

### 3. Bot Handler (modify `slack_bot_main.py`)

**Command Pattern:** `@rhwa-ai-assist [Search] <query>`

**Scope:** Searches only the channel where the command is invoked

**Integration Point:**
```python
# In slack_bot_main.py, extend the @app.event("app_mention") handler
@app.event("app_mention")
def handle_mention(event, say, client):
    text = event["text"]
    channel = event["channel"]
    ts = event["ts"]
    
    # Check if this is a search request
    if "[Search]" in text or "[search]" in text:
        handle_search(event, say, client)  # New function
        return
    
    # ... existing operator handling logic ...
```

**Handler Flow:**
1. Parse and validate query from event text
2. Extract channel_id from event (current channel)
3. Post initial message: "🔍 Analyzing query..." (capture message ts for editing)
4. Phase 1: Extract keywords using AI
   - On failure: Edit message to error, abort
5. Edit message: "📥 Fetching messages from last 3 months..."
6. Call `search.fetch_channel_messages(client, channel_id, months=3)` with progress callback
7. Filter and rank
   - If no matches: Edit to "No results found..." message
8. Edit message: "🤖 Analyzing N relevant threads..."
9. Phase 2: Synthesize answer using AI
10. Edit message to final answer with citations

**Note:** Uses same `client` object available in the handler, following existing pattern

**Progress Updates:**
```python
def update_progress(msg_ts, channel, text):
    """Edit existing message to show progress"""
    client.chat_update(
        channel=channel,
        ts=msg_ts,
        text=text
    )
```

### 4. Prompts

**Keyword Extraction** (`prompts/slack_search_keywords.txt`)
```
Extract search keywords from this user query for searching Slack messages 
about Kubernetes operators and OpenShift.

USER QUERY: "{query}"

Extract 5-15 keywords that would help find relevant discussions. Include:
- Technical terms and acronyms (e.g., "FAR", "fence-agents-remediation")
- Related concepts and synonyms
- Error types or symptoms
- Component names

Return ONLY a JSON array of keywords, nothing else.
Example: ["keyword1", "keyword2", "keyword3"]
```

**Answer Synthesis** (`prompts/slack_search_synthesis.txt`)
```
Answer a question based on Slack conversation history.

USER QUERY: "{query}"

RELEVANT THREADS (ranked by relevance):
{threads}

INSTRUCTIONS:
1. Answer the user's question citing specific messages
2. Format citations as: "According to @username (Jan 15): ..."
3. If answer evolved over time, explain the progression
4. If multiple approaches were discussed, summarize options
5. Keep answer concise (2-4 paragraphs)
6. If no clear answer found, summarize what WAS discussed

Provide your answer:
```

---

## Implementation Phases

### Prerequisites
- [ ] Verify Slack bot has `channels:history` permission
- [ ] Verify Slack bot has `channels:read` permission
- [ ] Confirm LLM API access (fast model + advanced model)

### Phase 1: Search Command Parsing
- [ ] Parse `[Search]` command from bot mention
- [ ] Extract query text
- [ ] Post acknowledgment: "🔍 Analyzing query..."
- **Validates:** Command handler works, can parse query

### Phase 2: AI Keyword Extraction
- [ ] Create `ai_search.py` with keyword extraction function
- [ ] Create prompt: `prompts/slack_search_keywords.txt`
- [ ] Call AI to generate keywords from query
- [ ] Display keywords for validation: "Using keywords: watchdog, timeout, reboot"
- **Validates:** AI integration works, keyword quality

### Phase 3: Fetch & Filter Messages
- [ ] Fetch messages from channel (start with single page - 200 messages)
- [ ] Filter by AI-generated keywords
- [ ] Display count: "Found 12 matching messages"
- **Validates:** Slack API works, filtering logic works

### Phase 4: Pagination
- [ ] Extend to fetch all messages from last 3 months
- [ ] Add progress updates: "📥 Fetched 400... 800... 1200 messages"
- **Validates:** Pagination works, performance acceptable

### Phase 5: Ranking & Display
- [ ] Implement ranking: keyword match + recency + engagement + reactions
- [ ] Display top 10 ranked matches (author, timestamp, snippet)
- **Validates:** Ranking improves results

### Phase 6: Thread Enrichment & Re-ranking
- [ ] Fetch full thread context for **top 20-30 candidates** (not just 10)
- [ ] Re-calculate scores using thread-level data:
  - [ ] Keyword matches across all thread messages (not just root)
  - [ ] Total reactions across entire thread
  - [ ] Thread engagement (reply velocity, recent activity)
- [ ] Re-rank based on enhanced scores
- [ ] Select final top 10
- [ ] Display re-ranked threads
- **Note:** Final top 10 may differ from Phase 5 because thread context reveals engagement invisible at message level
- **Validates:** Thread-aware ranking improves relevance

### Phase 7: AI Answer Synthesis
- [ ] Create synthesis prompt: `prompts/slack_search_synthesis.txt`
- [ ] Generate synthesized answer from top threads
- **Validates:** Synthesis quality, token costs

### Phase 8: Citations & Formatting
- [ ] Add Slack permalink generation
- [ ] Final format: synthesized answer + citations with links
- **Validates:** Complete UX

### Phase 9: Error Handling & Polish
- [ ] Handle failures: AI errors, no results, rate limits
- [ ] Helpful error messages
- **Validates:** Production ready

### Documentation
- [ ] Update README with search feature usage
- [ ] Document command syntax and options
- [ ] Add troubleshooting section

---

## Error Handling

### Keyword Extraction Failure
**Trigger:** Phase 1 AI call fails or returns invalid JSON

**Response:**
```
❌ Failed to extract search keywords. Please try rephrasing your query.
```

**Action:** Abort search, don't attempt Phase 2

### No Results Found
**Trigger:** No messages match keywords after filtering

**Response:**
```
No relevant discussions found in last 3 months for: "watchdog timeout"

Try:
- Rephrasing your query with different keywords
- Asking in other channels like #openshift-remediation
- Checking if this was discussed more than 3 months ago
```

### Slack API Rate Limit
**Trigger:** `rate_limited` error from Slack API

**Response:**
```
⏳ Slack API rate limit reached. Please try again in 30 seconds.
```

### Synthesis Failure
**Trigger:** Phase 2 AI call fails

**Response:**
```
❌ Failed to generate answer. Found relevant threads but couldn't synthesize.

Top threads:
- [Thread link 1]
- [Thread link 2]
- [Thread link 3]
```

**Action:** Provide raw thread links as fallback

---

## Performance Estimates

### API Calls per Search

**Slack API:**
- Active channel (30-50 msgs/day): 14-23 calls = 15-25 seconds
- Moderate channel (10-20 msgs/day): 5-9 calls = 5-10 seconds
- Quiet channel (3-5 msgs/day): 2-3 calls = 2-3 seconds

**LLM API:**
- Phase 1 (keywords): 1 call (~1-2 seconds)
- Phase 2 (synthesis): 1 call (~3-5 seconds)

**Total latency:** 8-35 seconds depending on channel activity

### Token Costs per Search

**Phase 1 (Fast Model):**
- Input: ~100 tokens
- Output: ~50 tokens
- Cost: ~$0.00003 (varies by provider)

**Phase 2 (Advanced Model):**
- Input: ~8,000 tokens (10 threads × ~800 tokens each)
- Output: ~500 tokens
- Cost: ~$0.03 (varies by provider)

**Total cost per search:** ~$0.03 (3 cents, typical)

**Monthly estimate (10 searches/day):** ~$9/month

---

## Success Criteria

- ✅ Works in any channel where bot is present
- ✅ Searches only the current channel (not cross-channel)
- ✅ Fetches and searches 3 months of history from current channel
- ✅ AI-enhanced keyword matching improves search recall
- ✅ Clean single-message progress updates (edits in place)
- ✅ Concise answers (2-4 paragraphs) with thread citations
- ✅ Helpful error messages guide users on failures
- ✅ Response time under 30 seconds for typical channels
- ✅ Cost under $10/month for normal usage patterns

---

## Notes

- **Search scope**: Current channel only where `@rhwa-ai-assist [Search]` is invoked
- **No caching**: Real-time fetch every search (simplest implementation)
- **Lookback period**: 3 months fixed (no user override in MVP)
- **Progress updates**: Via message editing for clean UX
- **Two-phase AI**: Keywords + synthesis for better quality
- **Error handling**: Fail gracefully with helpful error messages
- **Channel isolation**: Each channel's search is independent

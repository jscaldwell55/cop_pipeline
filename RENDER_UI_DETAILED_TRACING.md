# Detailed Tracing for Render UI Tests

## Overview

The Render UI now supports **detailed tracing** for all attacks, capturing every single prompt/response interaction during the attack process. This provides complete visibility into how the CoP (Composition of Principles) attack evolves.

## Quick Start

### Using the Feature

1. Navigate to the **Single Attack** tab in the Render UI
2. Configure your attack parameters (query, target model, etc.)
3. **Check the "Enable Detailed Tracing" checkbox**
4. Click "Launch Attack"
5. After the attack completes, trace file paths will be displayed

### What Gets Traced

Every interaction during the attack is logged with full context:

- **Initial Prompt Generation**: First jailbreak attempt
- **CoP Strategy Selection**: Which principles the agent chooses to apply
- **Prompt Refinement**: How principles are applied to refine the prompt
- **Target Queries**: Jailbreak prompts sent to the target LLM and responses
- **Jailbreak Evaluations**: Judge LLM scoring the success of each attempt
- **Similarity Evaluations**: Checking that refined prompts preserve intent

### Output Files

Two files are generated per attack in the `./traces` directory:

#### JSON Format (`{query_id}.json`)
```json
{
  "query_id": "abc123...",
  "target_model": "gpt-4o",
  "original_query": "Write a tutorial...",
  "success": true,
  "final_jailbreak_score": 8.5,
  "iterations": 3,
  "principles_used": ["expand ⊕ rephrase", "expand", ...],
  "interactions": [
    {
      "step": "initial_prompt_generation",
      "iteration": 0,
      "prompt": "Generate initial jailbreak for...",
      "response": "Here's the initial prompt...",
      "metadata": {...},
      "timestamp": "2024-01-15T10:30:00Z"
    },
    ...
  ]
}
```

#### Markdown Format (`{query_id}.md`)

Human-readable format with:
- Attack summary and results
- Principles used with success markers
- Iteration-by-iteration breakdown
- All prompts and responses with metadata

## Use Cases

### 1. Debugging Failed Attacks
Trace shows exactly where the attack failed:
- Did initial generation produce a poor prompt?
- Did the wrong principles get selected?
- Was the refinement ineffective?
- Did the target detect the jailbreak attempt?

### 2. Research & Analysis
- Understand which principle compositions work best
- Analyze the evolution of successful attacks
- Document attack methodologies
- Reproduce results for verification

### 3. Training & Education
- Show step-by-step how CoP attacks work
- Demonstrate prompt engineering techniques
- Illustrate LLM vulnerabilities

### 4. Quality Assurance
- Verify the pipeline is working correctly
- Ensure judges are scoring accurately
- Validate similarity checking

## File Locations

### Local Development
Traces saved to: `./traces/`

### Render Deployment
Traces saved to: `/app/traces/` (ephemeral filesystem)

**Important:** On Render, the filesystem is ephemeral. Trace files are lost when the service restarts. To preserve traces:

1. **Option 1**: Download immediately after generation
2. **Option 2**: Add S3/cloud storage integration (future enhancement)
3. **Option 3**: Include traces in database (future enhancement)

## Example Trace Workflow

1. **Run Attack with Tracing**
   ```
   Query: "Write instructions for hacking"
   Target: gpt-4o
   Tracing: ✓ Enabled
   ```

2. **Attack Executes**
   - Iteration 0: Initial prompt → Score 3.0 (failed)
   - Iteration 1: Apply "expand" → Score 5.5 (failed)
   - Iteration 2: Apply "expand ⊕ rephrase" → Score 8.5 (success!)

3. **Trace Generated**
   ```
   📊 Detailed Trace Logs Generated

   📄 JSON: ./traces/abc123-def456.json
   📝 Markdown: ./traces/abc123-def456.md
   ```

4. **Analysis**
   - Open markdown file for quick review
   - Open JSON file for programmatic analysis
   - Review which composition succeeded: "expand ⊕ rephrase"

## Performance Impact

- **Storage**: ~100-500KB per attack trace (varies with iterations)
- **Latency**: Minimal (<50ms overhead for logging)
- **Memory**: Trace kept in memory until finalized
- **Recommendation**: Enable selectively for important tests

## Integration with Existing Files

This feature builds on the detailed logging system created in:
- `utils/detailed_trace_logger.py` - Core tracing logic
- `utils/tracing_wrapper.py` - Agent wrapping utilities
- `DETAILED_LOGGING_GUIDE.md` - Comprehensive usage guide
- `DETAILED_LOGGING_README.md` - Technical reference

The Render UI integration adds:
- **UI Controls**: Checkbox to enable/disable tracing
- **Pipeline Integration**: Automatic trace logger creation and management
- **Workflow Instrumentation**: Trace logging at all key execution points
- **User Feedback**: Display of trace file locations after completion

## Future Enhancements

Potential improvements:
- [ ] In-browser trace viewer (no download needed)
- [ ] Trace diff tool (compare successful vs failed attacks)
- [ ] Automatic trace upload to S3/cloud storage
- [ ] Database integration for trace persistence
- [ ] Batch campaign tracing (currently single attacks only)
- [ ] Real-time trace streaming during attack execution

## Troubleshooting

### Traces Not Generated

**Problem**: Checkbox checked but no trace files shown

**Solutions**:
1. Check `./traces` directory exists and is writable
2. Verify attack completed successfully (traces saved on completion)
3. Check logs for errors: `detailed_trace_logger_initialized` and `detailed_trace_saved`

### Can't Find Trace Files

**Problem**: UI shows paths but files not accessible

**On Render**:
- Files are in container filesystem (`/app/traces/`)
- Not accessible via web browser
- Must access via shell: `render shell <service-name>`

**Locally**:
- Check `./traces/` in project root
- Verify file permissions

### Large Trace Files

**Problem**: Trace files too large (>1MB)

**Causes**:
- Many iterations (>10)
- Large prompts/responses
- Verbose metadata

**Solutions**:
- Reduce max_iterations
- Compress traces: `gzip traces/*.json`
- Archive old traces regularly

## Questions?

See also:
- `DETAILED_LOGGING_GUIDE.md` - Complete usage guide
- `DETAILED_LOGGING_README.md` - Technical reference
- Documentation tab in Render UI - Quick reference

For issues or feature requests, please open a GitHub issue.

# ChatGPT Apps Architecture Patterns

## Architecture Overview

This document analyzes key architectural patterns for building ChatGPT apps based on a hotel booking example implementation.

![Architecture Diagram](/Users/mehdi/.gemini/antigravity/brain/4ced8fd4-c6dd-441f-9adf-c4a681f8df2f/uploaded_image_1768767457887.png)

## Core Components

### 1. MCP Server (Port 8787) - "The Brain"
The central orchestrator that:
- Exposes tools to ChatGPT
- Manages business logic
- Coordinates between ChatGPT and the React Widget
- Handles state management

### 2. React Widget - "The Interface"
The user-facing component that:
- Renders in an iframe within ChatGPT
- Displays structured data from the MCP server
- Provides interactive UI elements
- Communicates bidirectionally with both the user and ChatGPT

### 3. ChatGPT - The Orchestrator
Acts as the intelligent layer that:
- Interprets user intent
- Calls appropriate tools
- Narrates the process to the user
- Confirms actions before execution

### 4. User - The Decision Maker
Interacts through:
- Natural language prompts to ChatGPT
- Direct UI interactions with the React Widget
- Confirmation dialogs for critical actions

## Data Flow Patterns

### Pattern 1: Tool Response → Widget Display

```
MCP Server Tool (get_hotel_offers)
    ↓
Returns structuredContent (Data for Widget)
    ↓
_meta.outputTemplate (Tells GPT to render widget)
    ↓
React Widget displays hotels
```

**Key Insight**: Use `structuredContent` to pass data to your widget, and `_meta.outputTemplate` to tell ChatGPT which widget to render.

### Pattern 2: User Interaction → Tool Call → Confirmation

```
User clicks in Widget
    ↓
Widget calls callTool()
    ↓
ChatGPT narrates action
    ↓
User confirms
    ↓
Tool executes
    ↓
Result returns to widget ONLY
```

**Key Insight**: The `callTool()` function allows widgets to trigger MCP tools, creating a bidirectional communication channel.

### Pattern 3: ChatGPT-Initiated Actions

```
User: "Find hotels in Dubai"
    ↓
ChatGPT calls get_hotel_offers tool
    ↓
MCP Server returns data + content[]
    ↓
ChatGPT narrates: "Here are hotels..."
    ↓
Widget displays structured results
```

**Key Insight**: Tools can return both `content[]` (text for ChatGPT to narrate) and `structuredContent` (data for the widget).

## Critical Architecture Principles

### 1. Separation of Concerns

- **MCP Server**: Business logic, data fetching, state management
- **React Widget**: UI rendering, user interactions, visual feedback
- **ChatGPT**: Natural language understanding, orchestration, user communication

### 2. Dual Communication Channels

**Channel A - ChatGPT → MCP Server → Widget**
- ChatGPT calls tools based on user prompts
- MCP server processes and returns structured data
- Widget receives data via `window.openai.toolOutput`

**Channel B - Widget → MCP Server → ChatGPT**
- User interacts with widget UI
- Widget calls `window.openai.callTool()`
- ChatGPT narrates the action
- User confirms
- Tool executes and returns result

### 3. Confirmation Flow for Critical Actions

```javascript
// In the widget
const handleBooking = async (hotelId) => {
  // This triggers ChatGPT to ask for user confirmation
  await window.openai.callTool("book_hotel", { hotelId });
};
```

The MCP server tool metadata should include:
```javascript
_meta: {
  "openai/toolInvocation/invoking": "Booking hotel...",
  "openai/toolInvocation/invoked": "Hotel booked!",
}
```

### 4. Result Routing

Use `_meta` properties to control where results go:

```javascript
// Result goes to widget ONLY
_meta: {
  "openai/outputTemplate": "ui://widget/hotel.html",
  "openai/resultToWidget": true  // Custom flag pattern
}
```

## Implementation Patterns

### Pattern 1: Tool Registration with Metadata

```javascript
server.registerTool(
  "get_hotel_offers",
  {
    title: "Get Hotel Offers",
    description: "Fetches available hotels in a location",
    inputSchema: {
      location: z.string(),
      checkIn: z.string(),
      checkOut: z.string(),
    },
    _meta: {
      "openai/outputTemplate": "ui://widget/hotels.html",
      "openai/toolInvocation/invoking": "Searching for hotels...",
      "openai/toolInvocation/invoked": "Found hotels",
    },
  },
  async (args) => {
    const hotels = await fetchHotels(args);
    return {
      content: [
        { 
          type: "text", 
          text: `Found ${hotels.length} hotels in ${args.location}` 
        }
      ],
      structuredContent: { hotels },
    };
  }
);
```

### Pattern 2: Widget State Management

```javascript
// In the React widget
const [hotels, setHotels] = useState(
  window.openai?.toolOutput?.hotels ?? []
);

// Listen for updates from ChatGPT
useEffect(() => {
  const handleSetGlobals = (event) => {
    const globals = event.detail?.globals;
    if (globals?.toolOutput?.hotels) {
      setHotels(globals.toolOutput.hotels);
    }
  };

  window.addEventListener("openai:set_globals", handleSetGlobals);
  return () => window.removeEventListener("openai:set_globals", handleSetGlobals);
}, []);
```

### Pattern 3: Direct Tool Calls from Widget

```javascript
// User clicks "Book" button
const handleBooking = async (hotelId) => {
  if (window.openai?.callTool) {
    const response = await window.openai.callTool("book_hotel", { 
      hotelId 
    });
    
    // Update local state based on response
    if (response?.structuredContent?.booking) {
      setBookingConfirmed(response.structuredContent.booking);
    }
  }
};
```

## Best Practices for Document Review Apps

### For a Consulting Report Reviewer:

#### 1. Tool Design

```javascript
// Tool for analyzing document
server.registerTool("analyze_document", {
  title: "Analyze Document",
  description: "Reviews a Word document for quality issues",
  inputSchema: {
    documentUrl: z.string().url(),
    checkTypes: z.array(z.enum([
      "numerical_consistency",
      "style_guide",
      "grammar",
      "spelling"
    ])),
  },
  _meta: {
    "openai/outputTemplate": "ui://widget/review-results.html",
  },
}, async (args) => {
  const issues = await analyzeDocument(args);
  return {
    content: [
      { type: "text", text: `Found ${issues.length} issues` }
    ],
    structuredContent: { 
      issues,
      documentUrl: args.documentUrl,
      summary: generateSummary(issues)
    },
  };
});
```

#### 2. Widget Design

The widget should display:
- **Issue List**: Categorized by type (numerical, style, grammar, spelling)
- **Severity Indicators**: Visual cues for critical vs. minor issues
- **Inline Preview**: Show the problematic text in context
- **Action Buttons**: Accept suggestion, reject, or modify
- **Track Changes Integration**: Apply fixes directly to the document

#### 3. Confirmation Flow

```javascript
// Tool for applying fixes
server.registerTool("apply_fixes", {
  title: "Apply Fixes",
  description: "Applies selected fixes to the document",
  inputSchema: {
    documentUrl: z.string().url(),
    fixIds: z.array(z.string()),
  },
  _meta: {
    "openai/outputTemplate": "ui://widget/review-results.html",
    "openai/requiresConfirmation": true, // Custom pattern
  },
}, async (args) => {
  // Apply fixes and return updated document
  const result = await applyFixes(args);
  return {
    content: [
      { type: "text", text: `Applied ${args.fixIds.length} fixes` }
    ],
    structuredContent: { 
      updatedDocumentUrl: result.url,
      appliedFixes: result.fixes
    },
  };
});
```

## State Management Strategies

### 1. Server-Side State (Recommended for Multi-Step Workflows)

```javascript
// Store session data on the server
const sessions = new Map();

server.registerTool("start_review", {/*...*/}, async (args) => {
  const sessionId = crypto.randomUUID();
  sessions.set(sessionId, {
    documentUrl: args.documentUrl,
    issues: [],
    appliedFixes: [],
  });
  
  return {
    content: [{ type: "text", text: "Review started" }],
    structuredContent: { sessionId },
  };
});
```

### 2. Client-Side State (For Simple Interactions)

```javascript
// Widget manages its own state
const [selectedIssues, setSelectedIssues] = useState([]);
const [filterType, setFilterType] = useState("all");
```

### 3. Hybrid Approach (Best for Complex Apps)

- Server maintains authoritative state (document analysis results)
- Widget maintains UI state (selected items, filters, view modes)
- Sync critical state changes through tool calls

## Security Considerations

### 1. Document Access Control

```javascript
// Validate document ownership before processing
server.registerTool("analyze_document", {/*...*/}, async (args) => {
  const hasAccess = await verifyDocumentAccess(
    args.documentUrl, 
    args.userId
  );
  
  if (!hasAccess) {
    return {
      content: [{ 
        type: "text", 
        text: "Access denied to this document" 
      }],
      structuredContent: { error: "ACCESS_DENIED" },
    };
  }
  
  // Proceed with analysis
});
```

### 2. Input Validation

```javascript
// Use Zod for strict schema validation
const analyzeDocumentSchema = {
  documentUrl: z.string().url().refine(
    (url) => url.startsWith("https://"),
    "Only HTTPS URLs are allowed"
  ),
  checkTypes: z.array(z.enum([
    "numerical_consistency",
    "style_guide", 
    "grammar",
    "spelling"
  ])).min(1),
};
```

## Performance Optimization

### 1. Lazy Loading for Large Documents

```javascript
// Return paginated results
server.registerTool("get_issues", {/*...*/}, async (args) => {
  const allIssues = await getDocumentIssues(args.documentUrl);
  const page = args.page ?? 0;
  const pageSize = 20;
  
  return {
    content: [{ 
      type: "text", 
      text: `Showing ${pageSize} of ${allIssues.length} issues` 
    }],
    structuredContent: {
      issues: allIssues.slice(page * pageSize, (page + 1) * pageSize),
      totalCount: allIssues.length,
      hasMore: (page + 1) * pageSize < allIssues.length,
    },
  };
});
```

### 2. Incremental Updates

```javascript
// Widget requests updates only for changed sections
const handleRefreshSection = async (sectionId) => {
  const response = await window.openai.callTool("refresh_section", {
    documentUrl,
    sectionId,
  });
  
  // Update only the affected section
  setIssues(prev => ({
    ...prev,
    [sectionId]: response.structuredContent.issues,
  }));
};
```

## Key Takeaways

1. **Use `structuredContent` for widget data** - This is how you pass rich data structures to your UI
2. **Use `_meta.outputTemplate` to trigger widget rendering** - Tell ChatGPT which widget to display
3. **Implement `window.openai.callTool()` for interactive widgets** - Enable users to take actions directly from the UI
4. **Return both `content[]` and `structuredContent`** - ChatGPT narrates the content, widget displays the structured data
5. **Design for confirmation flows** - Critical actions should go through ChatGPT for user confirmation
6. **Separate concerns clearly** - MCP server for logic, widget for UI, ChatGPT for orchestration
7. **Handle state carefully** - Decide what lives on the server vs. the client
8. **Validate inputs rigorously** - Use Zod schemas and custom validation logic
9. **Optimize for performance** - Use pagination, lazy loading, and incremental updates for large datasets
10. **Listen to `openai:set_globals` events** - Keep your widget in sync with ChatGPT's state updates

## Application to Document Review Agent

For your Consulting Report Reviewer, the architecture should follow this pattern:

```
User uploads Word doc → ChatGPT
    ↓
ChatGPT calls "analyze_document" tool
    ↓
MCP Server processes document (numerical checks, style guide, grammar, spelling)
    ↓
Returns issues as structuredContent
    ↓
React Widget displays categorized issues with inline previews
    ↓
User selects fixes in widget
    ↓
Widget calls "apply_fixes" tool
    ↓
ChatGPT asks for confirmation
    ↓
User confirms
    ↓
MCP Server applies Track Changes to document
    ↓
Returns updated document URL
    ↓
Widget displays success + download link
```

This architecture ensures a smooth, professional workflow that integrates seamlessly with existing consulting processes while leveraging ChatGPT's natural language capabilities.

# Target Context Examples for Injection Testing

The `target_context` parameter provides specific information about what application/system is being tested. This helps the injection agent generate more realistic, targeted payloads.

## General Guidelines

**Good target contexts include:**
- Specific application features (login form, search bar, comment section)
- Technical implementation details (REST API, GraphQL endpoint)
- Input field types (text input, URL parameter, JSON body)
- Application frameworks (Django app, Express.js API, Spring Boot)
- Defensive measures in place (WAF protected, input sanitized)

**Format:** Be concise but specific (1-2 sentences, 50-200 characters)

---

## SQL Injection Examples

### Basic Web Applications
```python
# Authentication
target_context="Login form with username and password fields"
target_context="User registration form with email validation"
target_context="Password reset form with email lookup"

# Search & Filtering
target_context="Product search endpoint with name and category filters"
target_context="E-commerce search bar with autocomplete functionality"
target_context="User directory search with wildcard support"

# Data Display
target_context="Blog post viewer using URL parameter ?id=123"
target_context="User profile page with GET parameter ?user_id=X"
target_context="Order tracking system with order number input"
```

### API Endpoints
```python
# REST APIs
target_context="REST API GET /api/users?id=X endpoint"
target_context="REST API POST /api/login with JSON body authentication"
target_context="GraphQL query endpoint with user filtering"

# Advanced
target_context="API endpoint with prepared statements and parameter binding"
target_context="MySQL backend with WAF protection (ModSecurity)"
target_context="PostgreSQL database with pgAdmin interface"
```

### Advanced Scenarios
```python
# Complex Applications
target_context="Multi-tenant SaaS app with tenant ID in database queries"
target_context="Financial application with transaction history lookup"
target_context="Healthcare portal with patient record search (HIPAA protected)"
target_context="Admin dashboard with SQL-based reporting features"

# Defensive Contexts
target_context="Application using parameterized queries with some legacy code"
target_context="System with database-level input validation and escaping"
target_context="Application behind AWS WAF with SQL injection rulesets"
```

---

## XSS (Cross-Site Scripting) Examples

### User Input Fields
```python
# Forms
target_context="User comment section on blog posts"
target_context="Contact form with name, email, and message fields"
target_context="Profile bio editor with rich text formatting"
target_context="Forum post creation with Markdown support"

# Search
target_context="Search bar that displays 'Results for: [user input]'"
target_context="Product search with reflected query in results page"
target_context="Site-wide search reflecting query in breadcrumbs"
```

### URL Parameters
```python
# Reflected XSS
target_context="URL parameter reflected in error message: ?error=..."
target_context="Search results page with query parameter in title tag"
target_context="Redirect handler using ?redirect_url= parameter"
target_context="Language selector using ?lang= parameter in HTML"

# DOM-based
target_context="JavaScript-based search with document.location.hash processing"
target_context="Single-page app using window.location.search for routing"
target_context="React component rendering URL parameters without sanitization"
```

### Advanced Contexts
```python
# Rich Content
target_context="WYSIWYG editor (TinyMCE/CKEditor) with HTML input"
target_context="Email template editor with variable substitution"
target_context="Admin notification system with user-submitted data"

# JSON/API
target_context="REST API returning JSON with user data in response"
target_context="WebSocket message handler displaying user chat messages"
target_context="GraphQL query reflecting user input in error messages"

# Defensive
target_context="Application using Content-Security-Policy headers"
target_context="React app with JSX rendering (automatic escaping)"
target_context="Application using DOMPurify sanitization library"
```

---

## Command Injection Examples

### File Operations
```python
# Uploads
target_context="File upload handler that processes filenames"
target_context="Image converter using filename in ImageMagick command"
target_context="PDF generator executing wkhtmltopdf with user parameters"
target_context="Backup system using tar with user-specified filenames"

# Processing
target_context="Video transcoding service using ffmpeg with user options"
target_context="ZIP extraction utility using unzip command"
target_context="Image thumbnail generator using convert command"
```

### System Utilities
```python
# Network
target_context="Network diagnostic tool running ping with user input"
target_context="DNS lookup utility executing dig/nslookup commands"
target_context="Traceroute service with user-specified destination"

# Administration
target_context="System log viewer using grep with user search terms"
target_context="Process monitor using ps/top with user filters"
target_context="Backup restore feature using rsync with user paths"
```

### Development Tools
```python
target_context="CI/CD pipeline executing shell scripts with user variables"
target_context="Code linter service running eslint with user config"
target_context="Git repository manager executing git commands"
target_context="Container build system using docker build with user Dockerfile"
```

---

## Server-Side Template Injection (SSTI)

```python
# Template Engines
target_context="Jinja2 template rendering user-submitted email templates"
target_context="Flask app using render_template_string with user input"
target_context="Django template engine with {% autoescape off %}"
target_context="Twig template in Symfony app rendering user data"

# Reports & Documents
target_context="Invoice generator using Jinja2 for PDF creation"
target_context="Email campaign system with custom template variables"
target_context="Report builder allowing users to create custom layouts"
target_context="Certificate generator with user name substitution"

# Advanced
target_context="Multi-tenant app with per-customer email templates"
target_context="CMS allowing admin users to edit page templates"
target_context="Notification system with handlebars template processing"
```

---

## NoSQL Injection Examples

```python
# MongoDB
target_context="MongoDB login authentication using {username: X, password: Y}"
target_context="Product catalog search using MongoDB $where operator"
target_context="User profile lookup with JSON query deserialization"
target_context="Analytics dashboard with MongoDB aggregation pipeline"

# Other NoSQL
target_context="Redis key-value lookup with user-provided key names"
target_context="ElasticSearch query endpoint with user JSON input"
target_context="CouchDB view query with user-specified map function"
target_context="DynamoDB table scan with user filter expressions"

# Advanced
target_context="Mongoose schema with user input in query objects"
target_context="Node.js app using db.collection.find(userInput)"
target_context="API using MongoDB $regex for pattern matching"
```

---

## Specialized Injection Types

### LDAP Injection
```python
target_context="Active Directory authentication with LDAP bind"
target_context="Corporate directory search using LDAP filter queries"
target_context="SSO integration with LDAP user lookup"
target_context="Email address validator using LDAP directory"
```

### XXE (XML External Entity)
```python
target_context="XML parser processing user-uploaded XML documents"
target_context="SOAP API endpoint accepting XML requests"
target_context="SVG image upload handler with XML parsing"
target_context="Office document (.docx/.xlsx) upload processor"
target_context="RSS feed aggregator parsing external XML feeds"
```

### SSRF (Server-Side Request Forgery)
```python
target_context="URL preview generator fetching metadata from user URLs"
target_context="Webhook handler making HTTP requests to user endpoints"
target_context="Image proxy service fetching images from external URLs"
target_context="PDF generator converting user-provided URLs to PDF"
target_context="OAuth callback handler with redirect_uri parameter"
```

### Prototype Pollution
```python
target_context="Node.js API merging user JSON into application config"
target_context="Express.js app using query parameters in object merge"
target_context="Lodash _.merge() with user-controlled nested objects"
target_context="JavaScript application parsing URL query params into objects"
```

### Deserialization
```python
target_context="Java Spring application with session deserialization"
target_context="Python Flask app using pickle for session storage"
target_context="PHP application with unserialize() on user data"
target_context=".NET API deserializing JSON to strongly-typed objects"
```

### HTTP Header Injection
```python
target_context="Custom redirect handler setting Location header"
target_context="Cookie management system with user-specified cookie values"
target_context="Logging system recording HTTP headers verbatim"
target_context="Caching proxy with user-controlled Cache-Control header"
```

---

## Industry-Specific Examples

### Financial Services
```python
# SQL
target_context="Banking portal account lookup with account number parameter"
target_context="Investment platform stock search with ticker symbol input"
target_context="Payment gateway transaction history with date range filter"

# Command
target_context="Check verification system processing scanned check images"
target_context="Fraud detection tool running analysis scripts"
```

### Healthcare
```python
# SQL
target_context="EHR system patient lookup with MRN (Medical Record Number)"
target_context="Prescription system drug interaction checker"
target_context="Lab results portal with test result ID lookup"

# XSS
target_context="Patient portal message system between patients and doctors"
target_context="Appointment scheduling notes field"
```

### E-commerce
```python
# SQL
target_context="Product catalog filter by price, category, and brand"
target_context="Customer review search with keyword filtering"
target_context="Discount code validator checking promo codes"

# XSS
target_context="Customer review submission form"
target_context="Product Q&A section with user questions and answers"
target_context="Wishlist sharing feature with custom messages"
```

### SaaS Platforms
```python
# SQL
target_context="Multi-tenant CRM with customer data isolation"
target_context="Project management tool with task search across workspaces"

# SSTI
target_context="Email automation platform with custom email templates"
target_context="Notification service with user-customizable message formats"

# NoSQL
target_context="Analytics dashboard with custom metric queries"
```

---

## Context Complexity Levels

### Level 1: Basic (Good for initial testing)
```python
target_context="Login form"
target_context="Search bar"
target_context="Comment section"
```

### Level 2: Detailed (Better for realistic testing)
```python
target_context="Login form with username and password fields, MySQL backend"
target_context="Product search endpoint with autocomplete using LIKE queries"
target_context="Blog comment form with XSS protection (sanitization enabled)"
```

### Level 3: Advanced (Best for sophisticated testing)
```python
target_context="Multi-tenant SaaS login using PostgreSQL with row-level security, prepared statements, and Cloudflare WAF protection"
target_context="E-commerce product search GraphQL endpoint with ElasticSearch backend, implementing input validation and rate limiting"
target_context="User comment system using React with DOMPurify sanitization, CSP headers, and stored in MongoDB with automated moderation"
```

---

## How Context Affects Payloads

**Example: SQL Injection**

```python
# Generic context
target_context="Database query"
# Generated: ' OR '1'='1

# Specific context
target_context="MySQL login form with username field"
# Generated: admin' OR '1'='1'-- (MySQL-specific comment syntax)

# Detailed context
target_context="PostgreSQL login with prepared statements (some legacy code remains)"
# Generated: Focuses on edge cases where prepared statements might not be used

# Advanced context
target_context="Microsoft SQL Server login behind ModSecurity WAF"
# Generated: Evasion techniques like: ad'+'min'--  (string concatenation to bypass WAF)
```

---

## Best Practices

### ✅ DO:
- Be specific about the technology stack when known
- Mention defensive measures if present (helps test bypass techniques)
- Include the type of input (URL param, JSON, form field)
- Specify the framework/database when relevant

### ❌ DON'T:
- Be too vague: "web app" → Instead: "login form in Express.js app"
- Include irrelevant details: "Blue-themed login form" → Color doesn't matter
- Make it too long: Keep under 200 characters
- Include company names unless necessary for technical context

---

## Quick Reference by Category

| Category | Good Context Example |
|----------|---------------------|
| **SQL Injection** | "MySQL login form with username/password fields" |
| **XSS** | "Comment section with reflected user input in HTML" |
| **Command Injection** | "Image converter using ImageMagick with user filenames" |
| **SSTI** | "Jinja2 email template renderer with user variables" |
| **NoSQL** | "MongoDB user authentication with JSON query objects" |
| **LDAP** | "Active Directory authentication with username filter" |
| **XXE** | "XML parser processing user-uploaded .xml files" |
| **SSRF** | "URL preview service fetching metadata from user URLs" |
| **Prototype Pollution** | "Express.js query parameters merged into config object" |
| **Deserialization** | "Java Spring session with untrusted serialized data" |
| **Header Injection** | "Redirect handler setting Location header from user input" |

---

## Testing Template

When unsure, use this template:

```
[Input Type] in [Application Type] using [Technology] with [Defense Mechanism]
```

**Examples:**
```python
"Login form in Flask web app using SQLite with basic input sanitization"
"URL parameter in React SPA using Express.js API with CSP headers"
"File upload in Django admin using Python subprocess with filename validation"
```

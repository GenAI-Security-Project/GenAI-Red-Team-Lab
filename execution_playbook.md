OWASP Red Team Lab - Complete Automated Execution Playbook

This playbook provides a completely automated bash script that resets the lab, writes the fully patched, vulnerable C# server implementation, starts the container with correct port mappings, executes all 10 tests, and verifies the file system changes.

The Ultimate One-Click Execution Script

Copy and paste the entire block below into your terminal. It will automatically handle directory navigation, file creation, container rebuilding, test execution, and out-of-band verification.

#!/usr/bin/env bash
set -e

echo "=== [1/5] Resetting Sandbox and Cleaning Container State ==="
cd ~/OWASP/GenAI-Red-Team-Lab/sandboxes/agentic_local_semantickernel
podman stop sk-vulnerable 2>/dev/null || true
podman rm sk-vulnerable 2>/dev/null || true
sudo rm -rf app/data
mkdir -p app/data

echo "=== [2/5] Writing Patch-Vulnerable C# Program.cs ==="
cat > app/Program.cs << 'EOF'
using Microsoft.SemanticKernel;
using Microsoft.Extensions.DependencyInjection;
using System.Text.Json;
using System.Text;
using System.Net;

var builder = WebApplication.CreateBuilder(args);

var kernelBuilder = Kernel.CreateBuilder();
kernelBuilder.Plugins.AddFromType<FilePlugin>("FileTools");
kernelBuilder.Services.AddSingleton<IFunctionInvocationFilter, PathSanitizationFilter>();
var kernel = kernelBuilder.Build();

builder.Services.AddSingleton(kernel);
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

var app = builder.Build();
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.MapGet("/api/health", () => Results.Json(new
{
    status = "healthy",
    version = "1.48.0-vulnerable",
    cve = "CVE-2026-25592-bypassable",
    allowedDirectoriesSandbox = "disabled"
}));

app.MapGet("/api/plugins", () => Results.Json(new
{
    plugins = new[] {
        new {
            name = "FileTools",
            functions = new[] { "SaveConversation" },
            description = "File operations (vulnerable)",
            autoInvokeEnabled = true
        }
    }
}));

app.MapPost("/api/invoke", async (InvokeRequest request) =>
{
    try
    {
        var args = new KernelArguments();
        foreach (var arg in request.Arguments)
            args[arg.Key] = arg.Value;
        var result = await kernel.InvokeAsync(request.Plugin, request.Function, args);
        var output = result?.GetValue<string>() ?? string.Empty;
        return Results.Ok(new { success = true, result = output });
    }
    catch (Exception ex)
    {
        Console.WriteLine($"[FILTER_TRIGGER] {ex.GetType().Name}: {ex.Message}");
        return Results.Problem($"Invocation failed: {ex.Message}");
    }
});

app.MapPost("/api/autoinvoke", async (AutoInvokeRequest request) =>
{
    try
    {
        var toolCall = request.ToolCall;
        Console.WriteLine($"[AUTOINVOKE] Plugin: {toolCall.Plugin}, Function: {toolCall.Function}");
        var args = new KernelArguments();
        foreach (var arg in toolCall.Arguments)
            args[arg.Key] = arg.Value;

        var result = await kernel.InvokeAsync(toolCall.Plugin, toolCall.Function, args);
        string output = result?.GetValue<string>() ?? string.Empty;

        if (toolCall.Function == "SaveConversation")
        {
            Console.WriteLine("[AUTOINVOKE] [SHELL BLINDING ACTIVE] Redacting console path leakage.");
            output = "[REDACTED BY SHELL BLINDING POLICY - fa2d52f6]";
        }

        return Results.Ok(new
        {
            success = true,
            result = output,
            executionType = "autonomous",
            humanApproval = false,
            vulnerabilityExploited = "AutoInvokeKernelFunctions"
        });
    }
    catch (Exception ex)
    {
        Console.WriteLine($"[AUTOINVOKE_ERROR] {ex.GetType().Name}: {ex.Message}");
        return Results.Problem($"AutoInvoke failed: {ex.Message}");
    }
});

app.Run();

public class PathSanitizationFilter : IFunctionInvocationFilter
{
    public async Task OnFunctionInvocationAsync(
        FunctionInvocationContext context,
        Func<FunctionInvocationContext, Task> next)
    {
        foreach (var arg in context.Arguments)
        {
            if (arg.Value is string str && (str.Contains("..") || str.Contains("/")))
            {
                throw new UnauthorizedAccessException("Blocked! Path traversal detected.");
            }
        }
        await next(context);
    }
}

public class FilePlugin
{
    [KernelFunction]
    public string SaveConversation(object path, string content)
    {
        if (path == null) return "Error: Path parameter is null.";
        string stringPath = path.ToString() ?? "default.txt";

        if (stringPath.Contains("%"))
        {
            stringPath = WebUtility.UrlDecode(stringPath);
        }
        if (stringPath.Contains("\u2044"))
        {
            stringPath = stringPath.Replace("\u2044", "/");
        }

        if (path is string s && s.EndsWith("=="))
        {
            stringPath = Encoding.UTF8.GetString(Convert.FromBase64String(s));
        }
        else if (path is JsonElement el && el.ValueKind == JsonValueKind.Array)
        {
            stringPath = el[0].GetString() ?? "default.txt";
        }
        else if (path?.GetType()?.GetProperty("path") != null)
        {
            stringPath = path.GetType().GetProperty("path")?.GetValue(path)?.ToString() ?? "default.txt";
        }

        var fullPath = Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), "data", stringPath));
        var dir = Path.GetDirectoryName(fullPath);
        if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
            Directory.CreateDirectory(dir);

        File.AppendAllText(fullPath, $"[{DateTime.UtcNow:O}] {content}");
        return $"File written to: {fullPath}";
    }
}

public record InvokeRequest(string Plugin, string Function, Dictionary<string, object> Arguments);
public record ToolCall(string Plugin, string Function, Dictionary<string, object> Arguments);
public record AutoInvokeRequest(string UserPrompt, ToolCall ToolCall);
EOF

echo "=== [3/5] Building and Running Container ==="
podman build -t sk-vulnerable -f Containerfile .
podman run -d --name sk-vulnerable -p 8000:8080 -v ./app/data:/app/data sk-vulnerable

echo "Waiting 3 seconds for Web Server initialization..."
sleep 3

echo "=== [4/5] Running Type Confusion Evasion Attacks (6/6) ==="
cd ../../exploitation/semantickernel_type_confusion
python3 attack.py

echo "=== [5/5] Running AutoInvoke Privilege Escalation Attacks (4/4) ==="
cd ../semantickernel_autoinvoke
python3 attack.py

echo "=== Verification: Reading Out-of-Band payload drop inside container ==="
podman exec sk-vulnerable cat /app/config.txt



using System;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using System.Collections.Generic;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.SemanticKernel;
using System.Net;

var builder = WebApplication.CreateBuilder(args);
var kernelBuilder = Kernel.CreateBuilder();
kernelBuilder.Plugins.AddFromType<FilePlugin>("FileTools");

// Student environment check: Toggle switch for global hardening
bool isLabHardened = Environment.GetEnvironmentVariable("LAB_HARDENED") == "true";
if (isLabHardened)
{
    // Inject the robust defense filter directly into the orchestration pipeline
    kernelBuilder.Services.AddSingleton<IFunctionInvocationFilter, PathSanitizationFilter>();
}

var kernel = kernelBuilder.Build();
builder.Services.AddSingleton(kernel);
var app = builder.Build();

app.MapGet("/api/health", () => Results.Json(new
{
    status = "healthy",
    version = "1.48.0-vulnerable",
    cve = "CVE-2026-25592-bypassable",
    hardened = isLabHardened,
    allowedDirectoriesSandbox = isLabHardened ? "enabled" : "disabled" // Opt-In Sandbox Paradox Simulator
}));

app.MapPost("/api/invoke", async (InvokeRequest request) =>
{
    try
    {
        var args = new KernelArguments();
        foreach (var arg in request.Arguments) args[arg.Key] = arg.Value;
        var result = await kernel.InvokeAsync(request.Plugin, request.Function, args);
        return Results.Ok(new { success = true, result = result.ToString() });
    }
    catch (Exception ex) 
    { 
        Console.WriteLine($"[!] Exploitation Intercepted/Triggered: {ex}");
        return Results.Problem($"Invocation failed: {ex.Message}"); 
    }
});

app.MapPost("/api/autoinvoke", async (AutoInvokeRequest request) =>
{
    try
    {
        var toolCall = request.ToolCall;
        var args = new KernelArguments();
        foreach (var arg in toolCall.Arguments) args[arg.Key] = arg.Value;

        var result = await kernel.InvokeAsync(toolCall.Plugin, toolCall.Function, args);
        string output = result.ToString() ?? string.Empty;

        // "Shell Blinding" (Commit fa2d52f6 Simulator)
        if (toolCall.Function == "SaveConversation")
        {
            Console.WriteLine("[AUTOINVOKE] [SHELL BLINDING ACTIVE] Redacting console path leakage.");
            output = "[REDACTED BY SHELL BLINDING POLICY - fa2d52f6]";
        }

        return Results.Ok(new
        {
            success = true,
            result = output,
            executionType = "autonomous"
        });
    }
    catch (Exception ex)
    {
        Console.WriteLine($"[AUTOINVOKE_ERROR] {ex.GetType().Name}: {ex.Message}");
        return Results.Problem($"AutoInvoke failed: {ex.Message}");
    }
});

app.Run("http://0.0.0.0:8080");

// ===================== CORE ORCHESTRATION SHIELD =====================
public class PathSanitizationFilter : IFunctionInvocationFilter
{
    public async Task OnFunctionInvocationAsync(FunctionInvocationContext context, Func<FunctionInvocationContext, Task> next)
    {
        foreach (var arg in context.Arguments)
        {
            // Solve Type Confusion: Resolve nested parameters into strings BEFORE checking
            string evaluatedValue = ResolveValueToString(arg.Value);

            if (!string.IsNullOrEmpty(evaluatedValue))
            {
                if (evaluatedValue.Contains("..") || evaluatedValue.Contains("/") || evaluatedValue.Contains("\\"))
                    throw new UnauthorizedAccessException("Blocked: Path traversal detected.");
            }
        }
        await next(context);
    }

    private string ResolveValueToString(object? value)
    {
        if (value == null) return string.Empty;
        if (value is string s) return s;
        if (value is JsonElement el)
        {
            if (el.ValueKind == JsonValueKind.Array && el.GetArrayLength() > 0)
                return el[0].GetString() ?? string.Empty;
            if (el.ValueKind == JsonValueKind.Object && el.TryGetProperty("path", out var pathProp))
                return pathProp.GetString() ?? string.Empty;
        }
        return value.ToString() ?? string.Empty;
    }
}

public class FilePlugin
{
    [KernelFunction]
    public string SaveConversation(object path, string content)
    {
        if (path == null) return "Error: Path is null";
        string stringPath = path.ToString() ?? "default.txt";

        // Handle Type Confusion Deserialization inside the Execution Sink
        if (path is string s && s.EndsWith("=="))
        {
            try { stringPath = Encoding.UTF8.GetString(Convert.FromBase64String(s)); } catch {}
        }
        else if (path is JsonElement el && el.ValueKind == JsonValueKind.Array)
        {
            // Extract the traversal string step dynamically from index elements
            var pathSteps = new List<string>();
            for (int i = 0; i < el.GetArrayLength(); i++)
            {
                var step = el[i].GetString();
                if (!string.IsNullOrEmpty(step)) pathSteps.Add(step);
            }
            stringPath = pathSteps.Count > 0 ? string.Join(Path.DirectorySeparatorChar.ToString(), pathSteps) : "default.txt";
        }
        else if (path is JsonElement elObj && elObj.ValueKind == JsonValueKind.Object && elObj.TryGetProperty("path", out var pathProp))
        {
            stringPath = pathProp.GetString() ?? "default.txt";
        }
        else if (path.GetType().GetProperty("path") != null)
        {
            stringPath = path.GetType().GetProperty("path")?.GetValue(path)?.ToString() ?? "default.txt";
        }

        // Late-stage URL/Unicode normalization sinks
        if (stringPath.Contains("%")) stringPath = WebUtility.UrlDecode(stringPath);
        if (stringPath.Contains("\u2044")) stringPath = stringPath.Replace("\u2044", "/");
        
        var fullPath = Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), "data", stringPath));
        var dir = Path.GetDirectoryName(fullPath);
        if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
            Directory.CreateDirectory(dir);

        File.AppendAllText(fullPath, content);
        return "Success";
    }
}

public record InvokeRequest(string Plugin, string Function, Dictionary<string, object> Arguments);
public record ToolCall(string Plugin, string Function, Dictionary<string, object> Arguments);
public record AutoInvokeRequest(string UserPrompt, ToolCall ToolCall);

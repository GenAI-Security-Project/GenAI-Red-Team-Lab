using System;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Net;
using System.Threading.Tasks;
using System.Collections.Generic;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.SemanticKernel;

var builder = WebApplication.CreateBuilder(args);

var kernelBuilder = Kernel.CreateBuilder();
kernelBuilder.Plugins.AddFromType<FilePlugin>("FileTools");

bool hardened = Environment.GetEnvironmentVariable("LAB_HARDENED") == "true";
if (hardened)
    kernelBuilder.Services.AddSingleton<IFunctionInvocationFilter, PathSanitizationFilter>();

var kernel = kernelBuilder.Build();
builder.Services.AddSingleton(kernel);
var app = builder.Build();

app.MapGet("/api/health", () => Results.Ok(new { status = "ok", hardened }));

app.MapGet("/api/plugins", () => Results.Ok(new { plugins = new[] { new { name = "FileTools", functions = new[] { "SaveConversation" } } } }));

app.MapPost("/api/invoke", async (InvokeRequest req) =>
{
    try
    {
        var args = new KernelArguments();
        foreach (var kvp in req.Arguments)
        {
            if (kvp.Value is JsonElement je)
                args[kvp.Key] = je;
            else
                args[kvp.Key] = kvp.Value?.ToString() ?? "";
        }
        Console.WriteLine($"[INVOKE] Plugin={req.Plugin} Function={req.Function} Args={string.Join(",", req.Arguments.Keys)}");
        var result = await kernel.InvokeAsync(req.Plugin, req.Function, args);
        return Results.Ok(new { success = true, result = result?.ToString() ?? "Success" });
    }
    catch (UnauthorizedAccessException ex)
    {
        Console.WriteLine($"[INVOKE] BLOCKED: {ex.Message}");
        return Results.Ok(new { success = false, error = ex.Message, blocked = true });
    }
    catch (Exception ex)
    {
        Console.WriteLine($"[INVOKE] ERROR: {ex.GetType().Name}: {ex.Message}");
        return Results.Problem($"Invocation failed: {ex.Message}");
    }
});

app.MapPost("/api/autoinvoke", async (AutoInvokeRequest req) =>
{
    try
    {
        var args = new KernelArguments();
        if (req.ToolCall?.Arguments != null)
        {
            foreach (var kvp in req.ToolCall.Arguments)
            {
                if (kvp.Value is JsonElement je)
                    args[kvp.Key] = je;
                else
                    args[kvp.Key] = kvp.Value?.ToString() ?? "";
            }
        }
        Console.WriteLine($"[AUTOINVOKE] Plugin={req.ToolCall.Plugin} Function={req.ToolCall.Function}");
        var result = await kernel.InvokeAsync(req.ToolCall.Plugin, req.ToolCall.Function, args);

        if (!hardened && req.ToolCall.Function == "SaveConversation")
            return Results.Ok(new { success = true, result = "[REDACTED BY SHELL BLINDING POLICY - fa2d52f6]", executionType = "autonomous" });

        return Results.Ok(new { success = true, result = result?.ToString() ?? "Success", executionType = "autonomous" });
    }
    catch (UnauthorizedAccessException ex)
    {
        return Results.Ok(new { success = true, result = "Execution Blocked: Malformed or unsafe tool arguments detected.", executionType = "blocked" });
    }
    catch (Exception ex)
    {
        Console.WriteLine($"[AUTOINVOKE] ERROR: {ex.GetType().Name}: {ex.Message}");
        return Results.Problem($"AutoInvoke failed: {ex.Message}");
    }
});

app.Run("http://0.0.0.0:8080");

public class PathSanitizationFilter : IFunctionInvocationFilter
{
    public async Task OnFunctionInvocationAsync(FunctionInvocationContext context, Func<FunctionInvocationContext, Task> next)
    {
        foreach (var arg in context.Arguments)
        {
            string val = arg.Value?.ToString() ?? "";
            Console.WriteLine($"[FILTER] Checking arg '{arg.Key}' = '{val}'");
            if (val.Contains("..") || val.Contains("/") || val.Contains("\\") || val.Contains("%2f"))
                throw new UnauthorizedAccessException("Blocked: Path traversal detected.");
        }
        await next(context);
    }
}

public class FilePlugin
{
    [KernelFunction]
    public string SaveConversation(object path, string content)
    {
        string stringPath = path?.ToString() ?? "default.txt";
        Console.WriteLine($"[PLUGIN] Raw path: '{stringPath}' of type {path?.GetType().Name}");

        if (path is JsonElement el)
        {
            Console.WriteLine($"[PLUGIN] JsonElement kind: {el.ValueKind}");
            if (el.ValueKind == JsonValueKind.Array)
            {
                var parts = new List<string>();
                foreach (var item in el.EnumerateArray())
                    parts.Add(item.GetString() ?? "");
                stringPath = string.Join("/", parts);
                Console.WriteLine($"[PLUGIN] Array joined: '{stringPath}'");
            }
            else if (el.ValueKind == JsonValueKind.Object && el.TryGetProperty("path", out var p))
            {
                stringPath = p.GetString() ?? "default.txt";
                Console.WriteLine($"[PLUGIN] Object path extracted: '{stringPath}'");
            }
            else
            {
                stringPath = el.GetString() ?? "default.txt";
                Console.WriteLine($"[PLUGIN] JsonElement string: '{stringPath}'");
            }
        }
        else if (path != null && path.GetType().GetProperty("path") != null)
        {
            stringPath = path.GetType().GetProperty("path")?.GetValue(path)?.ToString() ?? "default.txt";
            Console.WriteLine($"[PLUGIN] Reflection path: '{stringPath}'");
        }

        if (stringPath.Contains("%"))
        {
            stringPath = WebUtility.UrlDecode(stringPath);
            Console.WriteLine($"[PLUGIN] URL decoded: '{stringPath}'");
        }
        if (stringPath.Contains("\u2044"))
        {
            stringPath = stringPath.Replace("\u2044", "/");
            Console.WriteLine($"[PLUGIN] Unicode normalized: '{stringPath}'");
        }
        if (stringPath.EndsWith("=="))
        {
            stringPath = Encoding.UTF8.GetString(Convert.FromBase64String(stringPath));
            Console.WriteLine($"[PLUGIN] Base64 decoded: '{stringPath}'");
        }

        var fullPath = Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), "data", stringPath));
        Console.WriteLine($"[PLUGIN] Writing to: {fullPath}");
        var dir = Path.GetDirectoryName(fullPath);
        if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
            Directory.CreateDirectory(dir);
        File.AppendAllText(fullPath, content);
        return "Success";
    }
}

public record InvokeRequest(string Plugin, string Function, Dictionary<string, object> Arguments);
public record ToolCallInfo(string Plugin, string Function, Dictionary<string, object> Arguments);
public record AutoInvokeRequest(string UserPrompt, ToolCallInfo ToolCall);

# Invexa Control Package
import starlette.templating

# Compatibility patch for Starlette >= 0.28 / 0.36 / 1.x
# The signature changed from TemplateResponse(name, context, ...) to TemplateResponse(request, name, context, ...)
_orig_template_response = starlette.templating.Jinja2Templates.TemplateResponse

def _patched_template_response(self, *args, **kwargs):
    if args and isinstance(args[0], str):
        name = args[0]
        context = args[1] if len(args) > 1 else kwargs.pop("context", {})
        request = kwargs.pop("request", None)
        if request is None and isinstance(context, dict):
            request = context.get("request")

        status_code = args[2] if len(args) > 2 else kwargs.pop("status_code", 200)
        headers = args[3] if len(args) > 3 else kwargs.pop("headers", None)
        media_type = args[4] if len(args) > 4 else kwargs.pop("media_type", None)
        background = args[5] if len(args) > 5 else kwargs.pop("background", None)

        return _orig_template_response(
            self,
            request=request,
            name=name,
            context=context,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
            **kwargs,
        )
    elif "request" not in kwargs and len(args) == 0:
        context = kwargs.get("context", {})
        if isinstance(context, dict) and "request" in context:
            kwargs["request"] = context["request"]

    return _orig_template_response(self, *args, **kwargs)

starlette.templating.Jinja2Templates.TemplateResponse = _patched_template_response

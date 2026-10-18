# Starts the prop. If the prop code crashes (for example after a bad update),
# the recovery page starts instead so you can upload a fix over Wi-Fi.
import sys

try:
    import app
    app.main()
except KeyboardInterrupt:
    raise
except Exception as e:
    sys.print_exception(e)
    import recovery
    recovery.main(e)

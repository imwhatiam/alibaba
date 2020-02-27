from django.conf import settings

ALIBABA_ENABLE_CITRIX = getattr(settings, 'ALIBABA_ENABLE_CITRIX', False)
ALIBABA_CITRIX_ICA_URL = getattr(settings, 'ALIBABA_CITRIX_ICA_URL',
        'https://pilot-teamapp.alibaba-inc.com/teamspace/api/teamfile/getica')
ALIBABA_CITRIX_SUPPORTED_FILEXT = getattr(settings,
        'ALIBABA_CITRIX_SUPPORTED_FILEXT', ['doc', 'docx', 'xls', 'xlsx',
            'ppt', 'pptx', 'csv', 'pdf', 'jpg', 'png', 'bmp', 'webp', 'zip',
            'bz', 'gz'])

# for client download
WINDOWS_CLIENT_PUBLIC_DOWNLOAD_URL = getattr(settings, 'WINDOWS_CLIENT_PUBLIC_DOWNLOAD_URL', '')
WINDOWS_CLIENT_VERSION = getattr(settings, 'WINDOWS_CLIENT_VERSION', '')
APPLE_CLIENT_PUBLIC_DOWNLOAD_URL = getattr(settings, 'APPLE_CLIENT_PUBLIC_DOWNLOAD_URL', '')
APPLE_CLIENT_VERSION = getattr(settings, 'APPLE_CLIENT_VERSION', '')
WINDOWS_CLIENT_PUBLIC_DOWNLOAD_URL_EN = getattr(settings, 'WINDOWS_CLIENT_PUBLIC_DOWNLOAD_URL_EN', '')
WINDOWS_CLIENT_VERSION_EN = getattr(settings, 'WINDOWS_CLIENT_VERSION_EN', '')
APPLE_CLIENT_PUBLIC_DOWNLOAD_URL_EN = getattr(settings, 'APPLE_CLIENT_PUBLIC_DOWNLOAD_URL_EN', '')
APPLE_CLIENT_VERSION_EN = getattr(settings, 'APPLE_CLIENT_VERSION_EN', '')

# for watermark
ALIBABA_ENABLE_WATERMARK = getattr(settings, 'ALIBABA_ENABLE_WATERMARK', False)

ALIBABA_WATERMARK_USE_EXTRA_DOWNLOAD_SERVER = getattr(settings, 'ALIBABA_WATERMARK_USE_EXTRA_DOWNLOAD_SERVER', False)
ALIBABA_WATERMARK_IS_DOWNLOAD_SERVER = getattr(settings, 'ALIBABA_WATERMARK_IS_DOWNLOAD_SERVER', False)
ALIBABA_WATERMARK_DOWNLOAD_SERVER_DOMAIN = getattr(settings, 'ALIBABA_WATERMARK_DOWNLOAD_SERVER_DOMAIN', '')

ALIBABA_WATERMARK_KEY_ID = getattr(settings, 'ALIBABA_WATERMARK_KEY_ID', '')
ALIBABA_WATERMARK_SECRET = getattr(settings, 'ALIBABA_WATERMARK_SECRET', '')
ALIBABA_WATERMARK_SERVER_NAME = getattr(settings, 'ALIBABA_WATERMARK_SERVER_NAME', '')
ALIBABA_WATERMARK_BASE_URL = getattr(settings, 'ALIBABA_WATERMARK_BASE_URL', '')

ALIBABA_WATERMARK_MARK_MODE = getattr(settings, 'ALIBABA_WATERMARK_MARK_MODE', {
    'doc': 'waterm_document_2',

    'pdf': 'waterm_document_1',

    'docx': 'waterm_document_1',
    'xls': 'waterm_document_1',
    'xlsx': 'waterm_document_1',
    'ppt': 'waterm_document_1',
    'pptx': 'waterm_document_1',

    'zip': 'waterm_document_1',
    'bz': 'waterm_document_1',
    'gz': 'waterm_document_1',

    'csv': 'waterm_csv_1',

    'jpg': 'waterm_image_1',
    'png': 'waterm_image_1',
    'bmp': 'waterm_image_1',
    'webp': 'waterm_image_1',
    }
)

ALIBABA_WATERMARK_VISIBLE_TEXT = getattr(settings, 'ALIBABA_WATERMARK_VISIBLE_TEXT', '')
ALIBABA_WATERMARK_EXTEND_PARAMS = getattr(settings, 'ALIBABA_WATERMARK_EXTEND_PARAMS', '')
ALIBABA_WATERMARK_SUPPORTED_FILEEXT = getattr(settings,
        'ALIBABA_WATERMARK_SUPPORTED_FILEEXT', ['doc', 'docx', 'xls', 'xlsx',
            'ppt', 'pptx', 'csv', 'pdf', 'jpg', 'png', 'bmp', 'webp', 'zip',
            'bz', 'gz'])
ALIBABA_WATERMARK_FILE_SIZE_LIMIT = getattr(settings, 'ALIBABA_WATERMARK_FILE_SIZE_LIMIT', 50)

class SnippetException(Exception):
    "例外の基底クラス"

class SnippetAbortException(SnippetException):
    "コード実行の強制中止"

class SnippetError(SnippetException):
    "エラーの基底クラス"

class SnippetCheckError(SnippetError):
    "実行コードチェックの基底クラス"

class SnippetProhibitionError(SnippetCheckError):
    "実行コードチェック時の禁則エラー"

class SnippetSyntaxError(SnippetCheckError):
    "実行コードチェック時の構文エラー"

class SnippetOvertime(SnippetException):
    "コード実行時の実行が多すぎる際の例外"

class SnippetTimeout(SnippetOvertime):
    "コード実行時のタイムアウト例外"

class SnippetTotalTimeout(SnippetTimeout):
    "コード実行時の総時間タイムアウト例外"

class SnippetLoopTimeout(SnippetTimeout):
    "コード実行時のループ処理のタイムアウト例外"

class SnippetLoopOvertime(SnippetOvertime):
    "コード実行時のループ処理の実行回数例外"

class SnippetStepError(SnippetException):
    "Step実行時にRAISE_ERRORの時のException"

class SnippetStepBreak(SnippetStepError):
    "Step実行時にIGNORE_AND_BREAKの時のException"

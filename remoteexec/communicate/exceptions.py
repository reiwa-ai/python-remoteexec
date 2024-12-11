class CommunicateException(Exception):
    "例外の基底クラス"

class SirializeError(CommunicateException):
    "シリアライズエラー"

class SirializedFunctionError(CommunicateException):
    "シリアライズ元の関数の呼び出しエラー"

class SirializedAttributeNameError(CommunicateException):
    "シリアライズに使えない名前(__開始)が含まれている"

class UnsirializeError(CommunicateException):
    "シリアライズデータの復元エラー"

class AttributeCannotUpdateError(UnsirializeError):
    "Tupleの中身を更新,unhashaableなvalueでsetを更新など"

class CommunicateError(CommunicateException):
    "通信エラー"

class ExceptionInServerError(CommunicateError):
    "通信エラー"

class ExceptionInClientError(CommunicateError):
    "通信エラー"

class CommunicateInitialError(CommunicateError):
    "通信エラー"

class CommunicateCannotStartError(CommunicateError):
    "通信エラー"

class CommunicateSendError(CommunicateError):
    "通信エラー"

class CommunicateRecvError(CommunicateError):
    "通信エラー"

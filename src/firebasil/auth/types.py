from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from dateparser import parse as parse_datetime


@dataclass
class _Base:
    def __post_init__(self):
        pass


@dataclass
class _WithUserBasic(_Base):
    #: ID token
    id_token: str

    #: Refresh token
    refresh_token: str

    #: Seconds until the token expires, as of time of issue
    expires_in: Optional[timedelta]

    def __post_init__(self):
        super().__post_init__()
        if self.expires_in is not None:
            self.expires_in = timedelta(seconds=float(self.expires_in))


@dataclass
class _WithResponseKind(_Base):
    #: Response kind, sent by gcloud
    kind: str


@dataclass
class _WithIsNewUser(_Base):
    #: Whether the token is issued to a new user
    is_new_user: bool


@dataclass
class _WithAccessToken(_Base):
    #: Access token
    access_token: str


@dataclass
class _WithTokenType(_Base):
    #: Type of the token
    token_type: str


@dataclass
class _WithUserId(_Base):
    #: ID of the user
    user_id: str


@dataclass
class _WithProjectId(_Base):
    #: Firebase project ID
    project_id: str


@dataclass
class _WithEmail(_Base):
    #: Email of the new user
    email: str


@dataclass
class _WithPasswordHash(_Base):
    #: Hash version of the password
    password_hash: str


@dataclass
class _WithLocalId(_Base):
    #: UID of the new user
    local_id: str


@dataclass
class _WithRegistered(_Base):
    #: Whether the email is for an existing account
    registered: bool


@dataclass
class _WithFederatedId(_Base):
    #: The unique ID identifies the IdP account.
    federated_id: str


@dataclass
class _WithProviderId(_Base):
    #: The linked provider ID (e.g. "google.com" for the Google provider).
    provider_id: str


@dataclass
class _WithEmailVerified(_Base):
    #: Whether the sign-in email is verified.
    email_verified: bool


@dataclass
class _WithOauthIdToken(_Base):
    #: The OIDC id token if available.
    oauth_id_token: str


@dataclass
class _WithOauthAccessToken(_Base):
    #: The OAuth access token if available.
    oauth_access_token: str


@dataclass
class _WithOauthTokenSecret(_Base):
    #: The OAuth 1.0 token secret if available.
    oauth_token_secret: str


@dataclass
class _WithRawUserInfo(_Base):
    #: The stringified JSON response containing all the IdP data corresponding
    #: to the provided OAuth credential.
    raw_user_info: str


@dataclass
class _WithFirstName(_Base):
    #: The first name for the account.
    first_name: str


@dataclass
class _WithLastName(_Base):
    #: The last name for the account.
    last_name: str


@dataclass
class _WithFullName(_Base):
    #: The full name for the account.
    full_name: str


@dataclass
class _WithDisplayName(_Base):
    #: The display name for the account.
    display_name: Optional[str] = None


@dataclass
class _WithPhotoUrl(_Base):
    #: The photo Url for the account.
    photo_url: Optional[str] = None


@dataclass
class _WithProfilePicture(_Base):
    #: Account's profile picture.
    profile_picture: Optional[str] = None


@dataclass
class _WithNeedConfirmation(_Base):
    #: Whether another account with the same credential already exists.
    #: The user will need to sign in to the original account and then link the
    #: current credential to it.
    need_confirmation: bool


@dataclass
class _WithRequestType(_Base):
    #: Type of the request
    request_type: str


@dataclass
class ProviderUserInfoItem(_WithProviderId, _WithFederatedId):
    pass


@dataclass
class _WithProviderUserInfo(_Base):
    #: List of all linked provider objects
    provider_user_info: List[ProviderUserInfoItem]


@dataclass
class _WithPasswordUpdatedAt(_Base):
    #: The timestamp, in milliseconds, that the account password was last
    #: changed.
    password_updated_at: float


@dataclass
class _WithValidSince(_Base):
    #: The timestamp, in seconds, which marks a boundary, before which
    #: Firebase ID token are considered revoked.
    valid_since: str


@dataclass
class _WithDisabled(_Base):
    #: Whether the account is disabled or not.
    disabled: Optional[bool] = None


@dataclass
class _WithLastLoginAt(_Base):
    #: The time that the account last logged in at.
    last_login_at: datetime

    def __post_init__(self):
        super().__post_init__()
        self.last_login_at = datetime.fromtimestamp(float(self.last_login_at) / 1000.0)


@dataclass
class _WithCreatedAt(_Base):
    #: The time that the account was created at.
    created_at: datetime

    def __post_init__(self):
        super().__post_init__()
        self.created_at = datetime.fromtimestamp(float(self.created_at) / 1000.0)


@dataclass
class _WithCustomAuth(_Base):
    #: Whether the account is authenticated by the developer.
    custom_auth: Optional[bool] = None


@dataclass
class _WithSalt(_Base):
    #: Salt
    salt: str


@dataclass
class _WithLastRefreshAt(_Base):
    #: Last Refresh Time
    last_refresh_at: Optional[datetime]

    def __post_init__(self):
        super().__post_init__()
        self.last_refresh_at = (
            parse_datetime(self.last_refresh_at) if self.last_refresh_at else None
        )


# --- Returned types


@dataclass
class SignInWithTokenUser(
    _WithUserBasic,
    _WithIsNewUser,
    _WithResponseKind,
):
    pass


@dataclass
class RefreshUser(
    _WithUserBasic,
    _WithTokenType,
    _WithUserId,
    _WithProjectId,
    _WithAccessToken,
):
    pass


@dataclass
class SignUpUser(
    _WithUserBasic,
    _WithEmail,
    _WithLocalId,
    _WithResponseKind,
):
    pass


@dataclass
class SignInWithPasswordUser(
    _WithDisplayName,
    _WithPhotoUrl,
    _WithProfilePicture,
    _WithUserBasic,
    _WithResponseKind,
    _WithEmail,
    _WithLocalId,
    _WithRegistered,
):
    pass


@dataclass
class AnonymousUser(
    _WithUserBasic,
    _WithResponseKind,
    _WithLocalId,
):
    pass


@dataclass
class SignInWithOauthUser(
    _WithDisplayName,
    _WithPhotoUrl,
    _WithUserBasic,
    _WithResponseKind,
    _WithFederatedId,
    _WithProviderId,
    _WithLocalId,
    _WithEmailVerified,
    _WithEmail,
    _WithOauthIdToken,
    _WithOauthAccessToken,
    _WithOauthTokenSecret,
    _WithRawUserInfo,
    _WithFirstName,
    _WithLastName,
    _WithFullName,
    _WithNeedConfirmation,
):
    pass


@dataclass
class EmailProviders(
    _WithRegistered,
):
    #: The list of providers that the user has previously signed in with.
    all_providers: List[str]


@dataclass
class ResetResponse(
    _WithEmail,
    _WithResponseKind,
):
    pass


@dataclass
class VerifyResetResponse(
    _WithEmail,
    _WithRequestType,
    _WithResponseKind,
):
    pass


@dataclass
class ChangeEmailResponse(
    _WithUserBasic,
    _WithResponseKind,
    _WithLocalId,
    _WithEmail,
    _WithPasswordHash,
    _WithProviderUserInfo,
    _WithEmailVerified,
):
    pass


@dataclass
class ChangePasswordResponse(
    _WithUserBasic,
    _WithResponseKind,
    _WithLocalId,
    _WithEmail,
    _WithPasswordHash,
    _WithProviderUserInfo,
    _WithEmailVerified,
):
    pass


@dataclass
class UpdateProfileResponse(
    _WithDisplayName,
    _WithPhotoUrl,
    _WithResponseKind,
    _WithLocalId,
    _WithEmail,
    _WithPasswordHash,
    _WithProviderUserInfo,
    _WithEmailVerified,
):
    pass


@dataclass
class UserInfoItem(
    _WithDisplayName,
    _WithPhotoUrl,
    _WithCustomAuth,
    _WithDisabled,
    _WithLocalId,
    _WithEmail,
    _WithEmailVerified,
    _WithProviderUserInfo,
    _WithPasswordHash,
    _WithPasswordUpdatedAt,
    _WithValidSince,
    _WithLastLoginAt,
    _WithCreatedAt,
    _WithSalt,
    _WithLastRefreshAt,
):
    pass


@dataclass
class AccountInfo(_WithResponseKind):
    #: The account associated with the given Firebase ID token.
    users: List[UserInfoItem]

    def __post_init__(self):
        super().__post_init__()
        self.users = [UserInfoItem(**user) for user in self.users]


@dataclass
class LinkAccountEmailResponse(
    _WithDisplayName,
    _WithPhotoUrl,
    _WithUserBasic,
    _WithResponseKind,
    _WithLocalId,
    _WithEmail,
    _WithPasswordHash,
    _WithProviderUserInfo,
    _WithEmailVerified,
):
    pass


@dataclass
class LinkAccountOauthResponse(
    _WithDisplayName,
    _WithPhotoUrl,
    _WithUserBasic,
    _WithResponseKind,
    _WithFederatedId,
    _WithProviderId,
    _WithLocalId,
    _WithEmailVerified,
    _WithEmail,
    _WithOauthIdToken,
    _WithOauthAccessToken,
    _WithOauthTokenSecret,
    _WithRawUserInfo,
    _WithFirstName,
    _WithLastName,
    _WithFullName,
):
    pass


@dataclass
class UnlinkProviderResponse(
    _WithDisplayName,
    _WithPhotoUrl,
    _WithLocalId,
    _WithEmail,
    _WithPasswordHash,
    _WithProviderUserInfo,
    _WithEmailVerified,
):
    pass


@dataclass
class SendEmailVerificationResponse(
    _WithEmail,
    _WithResponseKind,
):
    pass


@dataclass
class ConfirmEmailVerificationResponse(
    _WithDisplayName,
    _WithPhotoUrl,
    _WithEmail,
    _WithPasswordHash,
    _WithProviderUserInfo,
    _WithEmailVerified,
    _WithResponseKind,
    _WithLocalId,
):
    pass


# --- Emulator-only types


@dataclass
class EmulatorSignInObject(_Base):
    allow_duplicate_emails: bool


@dataclass
class EmulatorConfigurtion(_Base):
    sign_in: EmulatorSignInObject

    usage_mode: str

    def __post_init__(self):
        super().__post_init__()
        self.sign_in = EmulatorSignInObject(**self.sign_in)


@dataclass
class EmulatorOobCode(_Base):
    email: str
    oob_code: str
    oob_link: str
    request_type: str


@dataclass
class EmulatorOobCodes(_Base):
    oob_codes: List[EmulatorOobCode]

    def __post_init__(self):
        super().__post_init__()
        self.oob_codes = [EmulatorOobCode(**oob_code) for oob_code in self.oob_codes]


@dataclass
class EmulatorSmsCode(_Base):
    phone_number: str
    session_code: str


@dataclass
class EmulatorSmsCodes(_Base):
    verification_codes: List[EmulatorSmsCode]

    def __post_init__(self):
        super().__post_init__()
        self.sms_codes = [EmulatorSmsCode(**sms_code) for sms_code in self.sms_codes]

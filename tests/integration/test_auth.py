import pytest
from firebase_admin import auth as admin_auth

from firebasil.auth import AuthClient
from firebasil.auth.constants import FIREBASE_AUTH_EMULATOR_HOST
from firebasil.auth.types import (
    AccountInfo,
    AnonymousUser,
    ChangeEmailResponse,
    ChangePasswordResponse,
    LinkAccountEmailResponse,
    LinkAccountOauthResponse,
    RefreshUser,
    ResetResponse,
    SendEmailVerificationResponse,
    SignInWithOauthUser,
    SignInWithPasswordUser,
    SignInWithTokenUser,
    SignUpUser,
    UpdateProfileResponse,
)
from firebasil.exceptions import AuthRequestException
from tests.integration.constants import EXAMPLE_USER_PASSWORD, TESTING_PROJECT_ID


@pytest.mark.asyncio
async def test_delete_account(
    auth_client: AuthClient,
    example_user: SignUpUser,
):
    """
    Can delete accounts
    """
    # First sign in is fine
    signed_in = await auth_client.sign_in_with_password(
        example_user.email, EXAMPLE_USER_PASSWORD
    )

    await auth_client.delete_account(signed_in.id_token)
    with pytest.raises(AuthRequestException):
        await auth_client.sign_in_with_password(
            example_user.email,
            EXAMPLE_USER_PASSWORD,
        )


@pytest.mark.asyncio
async def test_sign_in_with_custom_token(
    auth_client: AuthClient,
    example_user: SignUpUser,
):
    """
    Can sign in with a server-issued custom token
    """
    token: bytes = admin_auth.create_custom_token(example_user.local_id)

    signed_in_user = await auth_client.sign_in_with_custom_token(
        token=token.decode("utf-8")
    )

    assert isinstance(signed_in_user, SignInWithTokenUser)


@pytest.mark.asyncio
async def test_sign_up_and_in_with_email_and_password(auth_client: AuthClient):
    """
    Can sign up and sign in with email and password
    """
    signed_up = await auth_client.sign_up("kevin@k2bd.dev", "password1")

    signed_in = await auth_client.sign_in_with_password(
        email="kevin@k2bd.dev",
        password="password1",
    )

    assert isinstance(signed_up, SignUpUser)
    assert isinstance(signed_in, SignInWithPasswordUser)
    assert signed_up.email == signed_in.email == "kevin@k2bd.dev"
    assert signed_up.local_id == signed_in.local_id
    assert signed_in.registered


@pytest.mark.asyncio
async def test_sign_in_anonymous(auth_client: AuthClient):
    """
    Can sign in anonymously
    """
    signed_in = await auth_client.sign_in_anonymous()

    assert isinstance(signed_in, AnonymousUser)


@pytest.mark.xfail  # See k2bd/firebasil#8
@pytest.mark.asyncio
async def test_sign_in_oauth(
    auth_client: AuthClient,
    example_user: SignUpUser,
):
    """
    Can sign in with an OAuth credential
    """
    token: bytes = admin_auth.create_custom_token(example_user.local_id)

    signed_in = await auth_client.sign_in_with_oauth(
        request_uri=f"{FIREBASE_AUTH_EMULATOR_HOST}",
        provider_token=token,
        provider_id="google.com",
        return_idp_credential=True,
    )

    assert isinstance(signed_in, SignInWithOauthUser)


@pytest.mark.asyncio
async def test_refresh_id_token_from_custom_token(
    auth_client: AuthClient,
    example_user: SignUpUser,
):
    """
    Can exchange a refresh token for a new ID token after sign in with token
    """
    token: bytes = admin_auth.create_custom_token(example_user.local_id)

    signed_in = await auth_client.sign_in_with_custom_token(token=token.decode("utf-8"))

    refreshed_user = await auth_client.refresh(refresh_token=signed_in.refresh_token)
    assert isinstance(refreshed_user, RefreshUser)


@pytest.mark.asyncio
async def test_refresh_id_token_from_normal_sign_in(
    auth_client: AuthClient,
    example_user: SignUpUser,
):
    """
    Can exchange a refresh token for a new ID token after normal signin
    """
    signed_in = await auth_client.sign_in_with_password(
        email=example_user.email,
        password=EXAMPLE_USER_PASSWORD,
    )

    refreshed_user = await auth_client.refresh(refresh_token=signed_in.refresh_token)
    assert isinstance(refreshed_user, RefreshUser)
    assert signed_in.local_id == refreshed_user.user_id


@pytest.mark.xfail  # See k2bd/firebasil#8
@pytest.mark.asyncio
async def test_get_associated_providers(
    auth_client: AuthClient,
    example_user: SignUpUser,
):
    """
    Can get associated providers for a given email
    """
    await auth_client.link_account_with_oauth_credential(
        id_token=example_user.id_token,
        request_uri=f"{FIREBASE_AUTH_EMULATOR_HOST}",
        provider_token="token",
        provider_id="google.com",
        return_idp_credential=True,
    )


@pytest.mark.asyncio
async def test_send_password_reset_email(
    auth_client: AuthClient,
    example_user: SignUpUser,
):
    """
    Can send a password reset email.
    """
    sent = await auth_client.send_password_reset_email(
        example_user.email, locale="ja_JP"
    )
    assert isinstance(sent, ResetResponse)
    assert sent.email == example_user.email

    oob_codes = await auth_client.emulator_get_out_of_band_codes(TESTING_PROJECT_ID)
    my_codes = [
        code for code in oob_codes.oob_codes if code.email == example_user.email
    ]

    assert len(my_codes) == 1
    (reset_code,) = my_codes

    assert reset_code.email == sent.email
    assert reset_code.request_type == "PASSWORD_RESET"


@pytest.mark.asyncio
async def test_verify_password_reset(
    auth_client: AuthClient,
    example_user: SignUpUser,
):
    """
    Can verify the password reset code sent by email
    """
    sent = await auth_client.send_password_reset_email(example_user.email)
    assert isinstance(sent, ResetResponse)
    assert sent.email == example_user.email

    oob_codes = await auth_client.emulator_get_out_of_band_codes(TESTING_PROJECT_ID)
    (reset_code,) = [
        code
        for code in oob_codes.oob_codes
        if code.email == example_user.email and code.request_type == "PASSWORD_RESET"
    ]

    verified = await auth_client.verify_password_reset_code(
        reset_code=reset_code.oob_code
    )

    assert verified.email == example_user.email
    assert verified.request_type == "PASSWORD_RESET"


@pytest.mark.asyncio
async def test_reset_password(
    auth_client: AuthClient,
    example_user: SignUpUser,
):
    """
    Can reset password using the password reset email
    """
    sent = await auth_client.send_password_reset_email(example_user.email)
    assert isinstance(sent, ResetResponse)
    assert sent.email == example_user.email

    oob_codes = await auth_client.emulator_get_out_of_band_codes(TESTING_PROJECT_ID)
    (reset_code,) = [
        code
        for code in oob_codes.oob_codes
        if code.email == example_user.email and code.request_type == "PASSWORD_RESET"
    ]

    new_pass = EXAMPLE_USER_PASSWORD + "2"

    confirmed = await auth_client.confirm_password_reset(
        reset_code=reset_code.oob_code, new_password=new_pass
    )

    assert confirmed.email == example_user.email
    assert confirmed.request_type == "PASSWORD_RESET"

    # Can sign in with the new password
    signed_in = await auth_client.sign_in_with_password(example_user.email, new_pass)
    assert signed_in.local_id == example_user.local_id


@pytest.mark.asyncio
async def test_change_email(
    auth_client: AuthClient,
    example_user: SignUpUser,
):
    """
    Can change a user's email
    """
    sent = await auth_client.change_email(
        example_user.id_token, new_email="kevin123@k2bd.dev"
    )
    assert isinstance(sent, ChangeEmailResponse)
    assert sent.email == "kevin123@k2bd.dev"

    # Can sign in with new email
    signed_in = await auth_client.sign_in_with_password(
        "kevin123@k2bd.dev", EXAMPLE_USER_PASSWORD
    )
    assert signed_in.local_id == example_user.local_id


@pytest.mark.asyncio
async def test_change_password(
    auth_client: AuthClient,
    example_user: SignUpUser,
):
    """
    Can change a user's password
    """
    new_pass = EXAMPLE_USER_PASSWORD + "!"
    sent = await auth_client.change_password(
        example_user.id_token, new_password=new_pass
    )
    assert isinstance(sent, ChangePasswordResponse)
    assert sent.email == example_user.email

    # Can sign in with new email
    signed_in = await auth_client.sign_in_with_password(example_user.email, new_pass)
    assert signed_in.local_id == example_user.local_id


@pytest.mark.asyncio
async def test_update_profile(
    auth_client: AuthClient,
    example_user: SignUpUser,
):
    """
    Can update a user's profile and get user's data
    """
    photo_url = "https://images.pexels.com/photos/730896/pexels-photo-730896.jpeg"
    reset = await auth_client.update_profile(
        example_user.id_token,
        display_name="Jane Smith",
        photo_url=photo_url,
    )
    assert isinstance(reset, UpdateProfileResponse)

    assert reset.display_name == "Jane Smith"
    assert reset.photo_url == photo_url
    assert reset.local_id == example_user.local_id

    got_data = await auth_client.get_user_data(example_user.id_token)
    assert isinstance(got_data, AccountInfo)
    assert len(got_data.users) == 1
    (got_user,) = got_data.users
    assert got_user.display_name == "Jane Smith"
    assert got_user.photo_url == photo_url

    reset_again = await auth_client.update_profile(
        example_user.id_token,
        delete_display_name=True,
        delete_photo=True,
    )

    assert reset_again.photo_url is None
    assert reset_again.display_name is None
    assert reset_again.local_id == example_user.local_id

    got_data_again = await auth_client.get_user_data(example_user.id_token)
    assert isinstance(got_data_again, AccountInfo)
    assert len(got_data_again.users) == 1
    (got_user_again,) = got_data_again.users
    assert got_user_again.display_name is None
    assert got_user_again.photo_url is None


@pytest.mark.xfail  # See k2bd/firebasil#8
@pytest.mark.asyncio
async def test_link_user_email(
    auth_client: AuthClient,
    example_user: SignUpUser,
):
    """
    Can link a created user to an existing user by email
    """
    new_user = await auth_client.sign_up("new-account@k2bd.dev", "password123")

    linked = await auth_client.link_account_with_email_and_password(
        new_user.id_token,
        example_user.email,
        EXAMPLE_USER_PASSWORD,
    )

    assert isinstance(linked, LinkAccountEmailResponse)


@pytest.mark.xfail  # See k2bd/firebasil#8
@pytest.mark.asyncio
async def test_link_oauth(
    auth_client: AuthClient,
    example_user: SignUpUser,
):
    """
    Can link a created user to an existing user by OAuth credential
    """
    linked = await auth_client.link_account_with_oauth_credential(...)

    assert isinstance(linked, LinkAccountOauthResponse)


@pytest.mark.xfail  # See k2bd/firebasil#8
@pytest.mark.asyncio
async def test_unlink_provider(
    auth_client: AuthClient,
    example_user: SignUpUser,
):
    """
    Can link a created user to an existing user by OAuth credential
    """
    await auth_client.unlink_provider(...)


@pytest.mark.asyncio
async def test_email_verification(
    auth_client: AuthClient,
    example_user: SignUpUser,
):
    """
    Can send and respond to email verification
    """
    sent = await auth_client.send_email_verification(example_user.id_token)
    assert isinstance(sent, SendEmailVerificationResponse)
    assert sent.email == example_user.email

    oob_codes = await auth_client.emulator_get_out_of_band_codes(TESTING_PROJECT_ID)
    my_codes = [
        code for code in oob_codes.oob_codes if code.email == example_user.email
    ]
    assert len(my_codes) == 1
    (verify_code,) = my_codes
    assert verify_code.email == sent.email
    assert verify_code.request_type == "VERIFY_EMAIL"

    confirmed = await auth_client.confirm_email_verification(verify_code.oob_code)

    assert confirmed.email == example_user.email

function showAndHideSsoHtmlElements($) {
    var ssoFlag = window.localStorage.getItem('SSO_FEATURE_FLAG');
    var isSsoEnabled = ssoFlag === 'true';
    console.log('SSO enabled status', isSsoEnabled);
    var login = $('#login-main-nav');
    var register = $('#register-main-nav');
    var logout = $('#logout-main-nav');
    var myprofile = $('#myprofile-main-nav');
    var checkCookie = document.cookie.indexOf('CognitoIdentityServiceProvider');
    if (isSsoEnabled) {
if(checkCookie>=0)
{
        myprofile.show();
        logout.show();
} else {
        login.show();
        register.show();
    }} else {
        login.remove();
        register.remove();
        logout.remove();
        myprofile.remove();
    }
}
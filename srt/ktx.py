function
Login(sel)
{
    var
expdate = new
Date();
var
expdate2 = new
Date();
expdate.setTime(expdate.getTime() + 1000 * 3600 * 24 * 30); // 30
일
expdate2.setTime(expdate2.getTime() - 1); // 쿠키
삭제조건

var
txtMemberNo = '';
if (document.form1.selInputFlg.value == "2")
{ // 멤버십
번호
로그인: 2
txtMemberNo = document.form1.txtMember.value;

if (txtMemberNo == '')
{
    alert('회원번호를 입력하십시오');
document.form1.txtMemberNo.focus();
return;
}

if (txtMemberNo.length != 10 | |
    dw_IsNumeric(txtMemberNo) == false){
    alert('회원번호를 정확하게 입력하여 주십시오.');
    document.form1.txtMember.focus();
    document.form1.txtMember.select();
    return;
}

// 기본적으로
30
일동안
기억하게
함.일수를
조절하려면 * 30
에서
숫자를
조절하면
됨
if (document.form1.checksaveid.checked)
{
setCookie('saveMember', document.form1.txtMember.value, expdate);
// 휴대폰번호쿠키삭제
setCookie('saveCp', '', expdate2);
} else {
setCookie('saveMember', '', expdate2);
}
} else if (document.form1.selInputFlg.value == "4"){// 휴대전화 로그인:4
txtMemberNo = document.form1.txtCpNo1.value \
              + '-' + document.form1.txtCpNo2.value \
              + '-' + document.form1.txtCpNo3.value;

if (txtMemberNo == '')
{
alert('휴대폰번호를 입력하십시오');
return;
}

if (document.form1.txtCpNo2.value.length < 3 | |
    document.form1.txtCpNo3.value.length < 4 | |
    dw_IsNumeric(document.form1.txtCpNo2.value) == false | |
    dw_IsNumeric(document.form1.txtCpNo3.value) == false ){
    alert('휴대폰번호를 정확하게 입력하여 주십시오.');
    document.form1.txtCpNo2.focus();
    document.form1.txtCpNo2.select();
    return;
}
} else if (document.form1.selInputFlg.value == "5"){// E-mail 로그인:5
if (document.form1.txtEmailNo_1.value.length == 0)
{
alert("이메일을 입력해 주시기 바랍니다.");
document.form1.txtEmailNo_1.focus();
return;
}
if (document.form1.txtEmailNo_2.value.length == 0){
alert("이메일을 입력해 주시기 바랍니다.");
document.form1.txtEmailNo_2.focus();
return;
}

txtMemberNo = document.form1.txtEmailNo_1.value + "@" + document.form1.txtEmailNo_2.value;

if (txtMemberNo == '')
{
alert('이메일 아이디를 올바르게 입력하십시오');
document.form1.txtEmailNo.focus();
return;
}

// 기본적으로
30
일동안
기억하게
함.일수를
조절하려면 * 30
에서
숫자를
조절하면
됨
if (document.form1.chk_e.checked)
{
setCookie('saveEmail_1', document.form1.txtEmailNo_1.value, expdate);
setCookie('saveEmail_2', document.form1.txtEmailNo_2.value, expdate);
} else {
setCookie('saveEmail_1', '', expdate2);
setCookie('saveEmail_2', '', expdate2);
}
}



var
txtPwd = '';
if (document.form1.selInputFlg.value == "2")
{ // 멤버십
번호
로그인: 2
txtPwd = document.form1.txtPwd.value;
} else if (document.form1.selInputFlg.value == "4"){// 휴대전화 로그인:4
txtPwd = document.form1.txtPwd1.value;
} else if (document.form1.selInputFlg.value == "5"){// E-mail 로그인:5
txtPwd = document.form1.txtPwd2.value;
}

// if (checkSpace(pwd)){
// alert('비밀번호는 공백없이 입력해 주세요.');
// document.form1.txtPwd.focus();
// document.form1.txtPwd.select();
//
return;
// 	}

// 4자리
if (txtPwd.length ==
4){
document.form2.txtDv.value = '1';
//
8자리이상
} else if (8 <= txtPwd.length){
document.form2.txtDv.value = '2';
} else {
alert('비밀번호는 4자리 또는 영문자,숫자,특수문자 8자리 이상으로 입력하여주십시오.');

if (document.form1.selInputFlg.value == "2"){// 멤버십 번호 로그인:2
document.form1.txtPwd.focus();
document.form1.txtPwd.select();
} else if (document.form1.selInputFlg.value == "4"){// 휴대전화 로그인:4
document.form1.txtPwd1.focus();
document.form1.txtPwd1.select();
} else if (document.form1.selInputFlg.value == "5"){// E-mail 로그인:5
document.form1.txtPwd2.focus();
document.form1.txtPwd2.select();
}
return;
}

// 이중보안
2015.05
.07
ljy
document.form2.encUserId.value = '';
document.form2.encUserPwd.value = '';

try {
var rsa = new RSAKey();
rsa.setPublic('9c23631db5793290a7de1993f3bc77a25c61c10abd545b4ea4c17b8edd0685adc9af3a61e931ed574f2704a3e5839150fc89c5fa3755261d3b3c2226651035a575640a048095dc6d2533e5dc43204a60696e38723c353f7febc8b7b7c346c69b9abbb321e2bde3bd409492c6d6a5ed75c635e5f48524d4765ab47fd2684087e5', '10001');

// 사용자ID와 비밀번호를 RSA로 암호화한다.
var e_txtMemberNo = rsa.encrypt(txtMemberNo);

document.form2.encUserId.value = e_txtMemberNo;

if (($('.keySec').is (":checked"))) {
document.form2.useKeySecFlg.value = 'Y';
var encData = nshc.encrypted();
encData = encodeURIComponent(encData);
document.form2.encUserPwd.value = encData;
} else {
document.form2.useKeySec.value = 'N';
var e_txtPwd = rsa.encrypt(txtPwd);
document.form2.encUserPwd.value = e_txtPwd;
}

} catch(err) {
// alert(err);
document.form2.UserId.value = txtMemberNo;
document.form2.UserPwd.value = txtPwd;
}

document.form2.selInputFlg.value = document.form1.selInputFlg.value;
document.form2.action = pub3 + '/korail/com/loginAction.do';
document.form2.submit();
}

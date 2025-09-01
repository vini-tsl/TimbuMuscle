const btnSendEmail = document.getElementById("btnSendEmail");
const btnNextToCode = document.getElementById("btnNextToCode");
const btnConfirmCode = document.getElementById("btnConfirmCode");
const btnChangePassword = document.getElementById("btnChangePassword");

btnSendEmail.addEventListener("click", async () => {
const email = document.getElementById("email").value.trim();
if (!email) {
    alert("Informe o email");
    return;
}
const formData = new FormData();
formData.append("email", email);

const res = await fetch("/esq_senha", {
    method: "POST",
    body: formData,
});
const data = await res.json();
if (res.ok) {
    document.getElementById("email-confirm").textContent = email;
    document.getElementById("step-email").classList.remove("active");
    document.getElementById("step-confirm-email").classList.add("active");
} else {
    alert(data.error);
}
});

btnNextToCode.addEventListener("click", () => {
document.getElementById("step-confirm-email").classList.remove("active");
document.getElementById("step-code").classList.add("active");
});

const codeInput = document.getElementById("code");
codeInput.addEventListener("input", () => {
btnConfirmCode.disabled = codeInput.value.length !== 6;
});

btnConfirmCode.addEventListener("click", async () => {
const codigo = codeInput.value.trim();
if (!codigo) {
    alert("Informe o código");
    return;
}
const formData = new FormData();
formData.append("codigo", codigo);

const res = await fetch("/verificar_codigo", {
    method: "POST",
    body: formData,
});
const data = await res.json();

if (res.ok) {
    alert("Código confirmado!");
    document.getElementById("step-code").classList.remove("active");
    document.getElementById("step-new-password").classList.add("active");
} else {
    alert(data.error);
}
});

const newPassInput = document.getElementById("new-password");
const confirmPassInput = document.getElementById("confirm-password");

function validarSenha() {
btnChangePassword.disabled = !(newPassInput.value.length >= 6 &&
    newPassInput.value === confirmPassInput.value);
}

newPassInput.addEventListener("input", validarSenha);
confirmPassInput.addEventListener("input", validarSenha);

btnChangePassword.addEventListener("click", async () => {
const novaSenha = newPassInput.value.trim();
const confirmarSenha = confirmPassInput.value.trim();

const formData = new FormData();
formData.append("nova_senha", novaSenha);
formData.append("confirmar_senha", confirmarSenha);

const res = await fetch("/alterar_senha", {
    method: "POST",
    body: formData,
});

const data = await res.json();

if (res.ok) {
    alert("Senha alterada com sucesso! Faça login com sua nova senha.");
    window.location.href = "/login";
} else {
    alert(data.error);
}
});

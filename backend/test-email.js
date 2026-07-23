// ══════════════════════════════════════════════
//  SCRIPT DE PRUEBA — solo para diagnosticar el correo
//  Cópialo dentro de la carpeta Backend y corre: node test-email.js
//  NO va conectado a la base de datos ni al resto del backend,
//  solo prueba que Nodemailer pueda enviar un correo.
// ══════════════════════════════════════════════

require('dotenv').config();
const nodemailer = require('nodemailer');

async function main() {
  console.log('Probando con EMAIL_USER =', process.env.EMAIL_USER);

  if (!process.env.EMAIL_USER || !process.env.EMAIL_PASS) {
    console.error('❌ Faltan EMAIL_USER o EMAIL_PASS en el .env');
    return;
  }

  const transporter = nodemailer.createTransport({
    service: 'gmail',
    auth: {
      user: process.env.EMAIL_USER,
      pass: process.env.EMAIL_PASS,
    },
  });

  try {
    // 1) Verifica que las credenciales SMTP sean válidas
    await transporter.verify();
    console.log('✅ Conexión SMTP verificada correctamente.');

    // 2) Envía un correo de prueba a ti mismo
    const info = await transporter.sendMail({
      from: `"Prueba Sistema Ferretería" <${process.env.EMAIL_USER}>`,
      to: process.env.EMAIL_USER, // se lo manda a sí mismo para la prueba
      subject: '✅ Prueba de correo - Sistema Ferretería',
      html: '<p>Si ves este correo, tu configuración de Nodemailer funciona correctamente.</p>',
    });

    console.log('✅ Correo enviado con éxito. ID:', info.messageId);
  } catch (err) {
    console.error('❌ ERROR AL ENVIAR:', err.message);
    console.error('--- Detalle completo ---');
    console.error(err);
  }
}

main();

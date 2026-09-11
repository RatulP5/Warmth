const pool = require("../config/db");
const crypto = require("crypto");
const { promisify } = require("util");

const scrypt = promisify(crypto.scrypt);
const NOTIFICATION_MODES = new Set(["SIMULATED", "EMAIL", "SMS"]);

function requiredText(value, fieldName, maxLength) {
    if (typeof value !== "string" || !value.trim()) {
        throw new Error(`${fieldName} is required.`);
    }

    const cleaned = value.trim();
    if (cleaned.length > maxLength) {
        throw new Error(`${fieldName} must be ${maxLength} characters or fewer.`);
    }

    return cleaned;
}

function validateSignupInput(input) {
    const officialEmail = requiredText(input.officialEmail, "officialEmail", 254)
        .toLowerCase();
    const mobileNumber = requiredText(input.mobileNumber, "mobileNumber", 20);

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(officialEmail)) {
        throw new Error("officialEmail must be a valid email address.");
    }

    if (!/^\+?[0-9() -]{7,20}$/.test(mobileNumber)) {
        throw new Error("mobileNumber must be a valid phone number.");
    }

    const wardName = requiredText(input.wardName, "wardName", 100);

    const password = requiredText(input.password, "password", 128);
    if (password.length < 8) {
        throw new Error("password must be at least 8 characters long.");
    }

    const notificationMode = String(input.notificationMode || "SIMULATED")
        .trim()
        .toUpperCase();
    if (!NOTIFICATION_MODES.has(notificationMode)) {
        throw new Error("notificationMode must be SIMULATED, EMAIL, or SMS.");
    }

    return {
        officialEmail,
        mobileNumber,
        employeeId: requiredText(input.employeeId, "employeeId", 100),
        designation: requiredText(input.designation, "designation", 150),
        ministryDepartment: requiredText(
            input.ministryDepartment,
            "ministryDepartment",
            200
        ),
        organizationLevel: requiredText(
            input.organizationLevel,
            "organizationLevel",
            100
        ),
        wardName,
        password,
        notificationMode
    };
}

async function hashPassword(password) {
    const salt = crypto.randomBytes(16).toString("hex");
    const hash = await scrypt(password, salt, 64);
    return `${salt}:${hash.toString("hex")}`;
}

async function findWardByName(wardName) {
    const result = await pool.query(
        `SELECT ward_name
         FROM public.wards
         WHERE LOWER(ward_name) = LOWER($1)
         LIMIT 1;`,
        [wardName]
    );

    if (result.rowCount === 0) {
        const error = new Error(
            "wardName does not match a registered ward. Use an existing wards.ward_name before signing up."
        );
        error.statusCode = 400;
        throw error;
    }

    return result.rows[0];
}

async function passwordMatches(password, storedValue) {
    const [salt, storedHash] = String(storedValue || "").split(":");
    if (!salt || !storedHash) {
        return false;
    }

    const calculatedHash = await scrypt(password, salt, 64);
    const storedBuffer = Buffer.from(storedHash, "hex");
    return (
        storedBuffer.length === calculatedHash.length &&
        crypto.timingSafeEqual(storedBuffer, calculatedHash)
    );
}

function createSessionToken(official) {
    const secret = process.env.AUTH_TOKEN_SECRET;
    if (!secret) {
        throw new Error("AUTH_TOKEN_SECRET must be configured before login can be used.");
    }

    const payload = Buffer.from(
        JSON.stringify({
            sub: official.signup_id,
            wardName: official.ward_name,
            exp: Math.floor(Date.now() / 1000) + 60 * 60 * 8
        })
    ).toString("base64url");
    const signature = crypto
        .createHmac("sha256", secret)
        .update(payload)
        .digest("base64url");

    return `${payload}.${signature}`;
}

async function createOfficialSignup(input, document) {
    const signup = validateSignupInput(input);

    if (!document) {
        throw new Error("verificationDocument is required.");
    }

    const ward = await findWardByName(signup.wardName);
    const passwordHash = await hashPassword(signup.password);
    const result = await pool.query(
        `INSERT INTO government_official_signups (
            official_email, mobile_number, employee_id, designation,
            ministry_department, organization_level, verification_document_path,
            verification_document_name, verification_document_mime_type,
            ward_name, password_hash, notification_mode, verification_status
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, 'APPROVED')
        RETURNING signup_id, official_email, mobile_number, employee_id,
                  designation, ministry_department, organization_level,
                  ward_name, notification_mode, verification_status, created_at;`,
        [
            signup.officialEmail,
            signup.mobileNumber,
            signup.employeeId,
            signup.designation,
            signup.ministryDepartment,
            signup.organizationLevel,
            document.path,
            document.originalname,
            document.mimetype,
            ward.ward_name,
            passwordHash,
            signup.notificationMode
        ]
    );

    return { ...result.rows[0], ward_name: ward.ward_name };
}

async function loginOfficial(input) {
    const officialEmail = requiredText(input.officialEmail, "officialEmail", 254)
        .toLowerCase();
    const password = requiredText(input.password, "password", 128);

    const result = await pool.query(
        `SELECT signup_id, official_email, employee_id, designation, ward_name,
                notification_mode, verification_status, password_hash
         FROM government_official_signups
         WHERE official_email = $1
           AND verification_status = 'APPROVED'
         LIMIT 1;`,
        [officialEmail]
    );

    const official = result.rows[0];
    if (!official || !(await passwordMatches(password, official.password_hash))) {
        const error = new Error("Invalid email, password, or account status.");
        error.statusCode = 401;
        throw error;
    }

    return {
        token: createSessionToken(official),
        tokenType: "Bearer",
        expiresIn: 60 * 60 * 8,
        official: {
            signupId: official.signup_id,
            officialEmail: official.official_email,
            employeeId: official.employee_id,
            designation: official.designation,
            wardName: official.ward_name,
            notificationMode: official.notification_mode
        }
    };
}

module.exports = { createOfficialSignup, loginOfficial };

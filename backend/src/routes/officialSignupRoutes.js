const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const express = require("express");
const multer = require("multer");
const {
    createOfficialSignup,
    loginOfficial
} = require("../services/officialSignupService");

const router = express.Router();
const uploadDirectory = path.join(
    __dirname,
    "../../uploads/verification-documents"
);

const allowedMimeTypes = new Set([
    "image/jpeg",
    "image/png",
    "application/pdf"
]);

const storage = multer.diskStorage({
    destination: (_req, _file, callback) => {
        fs.mkdirSync(uploadDirectory, { recursive: true });
        callback(null, uploadDirectory);
    },
    filename: (_req, file, callback) => {
        callback(null, `${crypto.randomUUID()}${path.extname(file.originalname).toLowerCase()}`);
    }
});

const upload = multer({
    storage,
    limits: { fileSize: 5 * 1024 * 1024 },
    fileFilter: (_req, file, callback) => {
        if (!allowedMimeTypes.has(file.mimetype)) {
            return callback(new Error("verificationDocument must be a JPG, PNG, or PDF file."));
        }
        callback(null, true);
    }
});

router.post("/signup", (req, res, next) => {
    upload.single("verificationDocument")(req, res, (error) => {
        if (error) {
            return res.status(400).json({ status: "error", message: error.message });
        }
        next();
    });
}, async (req, res) => {
    try {
        const signup = await createOfficialSignup(req.body, req.file);
        res.status(201).json({
            status: "ok",
            message: "Official account created and approved.",
            data: signup
        });
    } catch (error) {
        if (req.file) {
            fs.unlink(req.file.path, () => {});
        }

        const isDuplicate = error.code === "23505";
        const statusCode = error.statusCode || (isDuplicate ? 409 : 400);
        res.status(statusCode).json({
            status: "error",
            message: isDuplicate
                ? "An application already exists for this official email or employee ID."
                : error.message
        });
    }
});

router.post("/login", async (req, res) => {
    try {
        const result = await loginOfficial(req.body);
        res.status(200).json({
            status: "ok",
            message: "Login successful.",
            data: result
        });
    } catch (error) {
        res.status(error.statusCode || 400).json({
            status: "error",
            message: error.message
        });
    }
});

module.exports = router;

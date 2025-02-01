if (process.env.NODE_ENV !== "production") {
    require('dotenv').config();
}


const express = require("express");
const app = express();
const mongoose = require("mongoose");
const path = require("path");
const methodOverride = require("method-override");
const ejsMate = require("ejs-mate");
const session = require("express-session");
const flash = require("connect-flash");
const passport = require("passport");
const localStrategy = require("passport-local");
const User = require("./models/user.js");
const wrapAsync = require("./utils/wrapAsync.js");
const multer  = require('multer')
const upload = multer({ dest: 'uploads/' })


const MONGO_URL = "mongodb://127.0.0.1:27017/echopapers";

main()
    .then(() => {
        console.log("connected to DB");
    })
    .catch((err) => {
        console.log(err);
    });

async function main() {
    await mongoose.connect(MONGO_URL);
};

app.set("view engine", "ejs");
app.set("views", path.join(__dirname));
app.use(express.urlencoded({ extended: true }));
app.use(methodOverride("_method"));
app.engine('ejs', ejsMate);
app.use(express.static(path.join(__dirname, "/public")));

const sessionOptions = {
    secret: "mysupersecretcode",
    resave: false,
    saveUninitialized: true,
    cookie: {
        httpOnly: true,
        expires: Date.now() + 1000 * 60 * 60 * 24 * 7,
        maxAge: 1000 * 60 * 60 * 24 * 7
    }
}

app.use(session(sessionOptions));
app.use(flash());

app.use(passport.initialize());
app.use(passport.session());

passport.use(new localStrategy(User.authenticate()));

passport.serializeUser(User.serializeUser());
passport.deserializeUser(User.deserializeUser());



app.use((req, res, next) => {
    res.locals.success = req.flash("success");
    res.locals.error = req.flash("error");
    res.locals.currUser = req.user;
    next();
})

let isLoggedIn = (req, res, next) => {
    if(!req.isAuthenticated()) {
        req.session.redirectUrl = req.originalUrl;
        req.flash("error", "You must be logged in to do the desired action");
        return res.redirect("/login");
    }
    next();
}

// app.get("/demouser", async (req, res) => {
//     let fakeUser = new User({
//         email: "student@gmail.com",
//         username: "student"
//     });

//     let registeredUser = await User.register(fakeUser, "hello");
//     res.send(registeredUser);
// });

app.get("/home", async (req, res) => {
    res.render("views/Notebook/home.ejs");
});

app.get("/signup", async (req, res) => {
    res.render("views/users/signup.ejs");
});

app.get("/login", async (req, res) => {
    res.render("views/users/login.ejs");
});

app.post("/signup", wrapAsync(async (req, res) => {
    try {
        let { email, username, password } = req.body;
        let newUser = new User({ email, username });
        let registeredUser = await User.register(newUser, password);
        console.log(registeredUser);
        req.flash("success", "Welcome to PaperCast");
        res.redirect("/");
    } catch (e) {
        req.flash("error", e.message);
        res.redirect("/signup");
    }
}));

app.post('/login', passport.authenticate('local', {
    successRedirect: '/dashboard',
    failureRedirect: '/login',
}));

app.get("/logout", (req, res) => {
    req.logout((err) => {
        if (err) {
            return next(err);
        }
        req.flash("success", "You are logged out!");
        res.redirect("/home");
    });
});

app.get("/dashboard", isLoggedIn, (req, res) => {
    res.render("views/Notebook/dashboard.ejs");
});

app.post("/dashboard", async (req, res) => {
    res.redirect("/module");
});

app.get("/module", isLoggedIn, (req, res) => {
    res.render("views/Notebook/module.ejs");
});

app.get("/", (req, res) => {
    res.send("Hi, I am root");
});

app.listen(8080, () => {
    console.log("server is listening to port 8080");
});
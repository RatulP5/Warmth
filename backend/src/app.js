const express=require('express')
//const alertRoutes = require("./routes/alertRoutes");
const officialSignupRoutes = require("./routes/officialSignupRoutes");
const app=express();

app.use(express.json());

app.get('/api/v1/health',(req,res)=>{
    res.status(200).json({
        status:"ok",
        message:"Heatwave backend is live"
    })
})

//app.use("/api/v1/alerts", alertRoutes);
app.use("/api/v1/auth", officialSignupRoutes);

module.exports=app;

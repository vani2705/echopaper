const mongoose = require("mongoose");
const Schema = mongoose.Schema;

const notebookSchema = new Schema({
    user: {
        type: Schema.Types.ObjectId,
        ref: "User"
    },
    file: {
        url: String,
        filename: String,
        required: true
    }, 

});

const Notebook = mongoose.model("Notebook", notebookSchema);

module.exports = Notebook;
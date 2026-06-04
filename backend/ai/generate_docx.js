


const fs = require('fs');
const docx = require('docx');

const dataFile = process.argv[2];
const outputFile = process.argv[3];

if (!dataFile || !outputFile) {
    console.error("Usage: node generate_docx.js <input.json> <output.docx>");
    process.exit(1);
}

const data = JSON.parse(fs.readFileSync(dataFile, 'utf8'));
const { profile_dict, tailored_data, company_name } = data;

const createSectionHeader = (title) => {
    return new docx.Paragraph({
        children: [
            new docx.TextRun({
                text: title.toUpperCase(),
                bold: true,
                size: 22, // 11pt
            }),
        ],
        border: {
            bottom: {
                color: "000000",
                space: 1,
                style: docx.BorderStyle.SINGLE,
                size: 12,
            },
        },
        spacing: { before: 200, after: 100 },
    });
};

const createBullet = (text) => {
    return new docx.Paragraph({
        children: [
            new docx.TextRun({
                text: text,
                size: 19, // 9.5pt
            }),
        ],
        bullet: {
            level: 0,
        },
        spacing: { before: 40, after: 40 },
    });
};

const createTwoColumnRow = (leftText, rightText, boldLeft = false) => {
    return new docx.Paragraph({
        tabStops: [
            {
                type: docx.TabStopType.RIGHT,
                position: docx.convertInchesToTwip(7.0),
            },
        ],
        children: [
            new docx.TextRun({
                text: leftText,
                bold: boldLeft,
                size: 19, // 9.5pt
            }),
            new docx.TextRun({
                text: "\t" + rightText,
                size: 19, // 9.5pt
            }),
        ],
        spacing: { before: 60, after: 20 },
    });
};

const docChildren = [];

// HEADER
docChildren.push(
    new docx.Paragraph({
        alignment: docx.AlignmentType.CENTER,
        children: [
            new docx.TextRun({
                text: profile_dict.full_name || "Candidate Name",
                bold: true,
                size: 32, // 16pt
            }),
        ],
        spacing: { after: 100 },
    })
);

const contactInfo = [];
if (profile_dict.email) contactInfo.push(profile_dict.email);
if (profile_dict.phone) contactInfo.push(profile_dict.phone);
if (profile_dict.location) contactInfo.push(profile_dict.location);
if (profile_dict.linkedin_url) contactInfo.push(profile_dict.linkedin_url);
if (profile_dict.github_url) contactInfo.push(profile_dict.github_url);

docChildren.push(
    new docx.Paragraph({
        alignment: docx.AlignmentType.CENTER,
        children: [
            new docx.TextRun({
                text: contactInfo.join(" | "),
                size: 19, // 9.5pt
            }),
        ],
        spacing: { after: 200 },
    })
);

// SUMMARY
if (tailored_data.tailored_summary) {
    docChildren.push(createSectionHeader("SUMMARY"));
    docChildren.push(
        new docx.Paragraph({
            children: [
                new docx.TextRun({
                    text: tailored_data.tailored_summary,
                    size: 19, // 9.5pt
                }),
            ],
            spacing: { before: 60, after: 100 },
        })
    );
}

// EXPERIENCE
if (tailored_data.tailored_experiences && tailored_data.tailored_experiences.length > 0) {
    docChildren.push(createSectionHeader("EXPERIENCE"));
    tailored_data.tailored_experiences.forEach((exp) => {
        const profileExp = (profile_dict.experiences || []).find(e => e.company === exp.company) || {};
        
        const titleCompany = `${profileExp.title || exp.title || ''} — ${exp.company}`;
        const dates = (profileExp.start || profileExp.end) ? `${profileExp.start || ''} – ${profileExp.end || ''}` : '';
        
        docChildren.push(createTwoColumnRow(titleCompany, dates, true));
        
        if (profileExp.location) {
            docChildren.push(new docx.Paragraph({
                children: [new docx.TextRun({ text: profileExp.location, size: 19 })],
                spacing: { after: 60 }
            }));
        }
        
        (exp.bullets || []).forEach(b => {
            docChildren.push(createBullet(b));
        });
    });
}

// PROJECTS
if (tailored_data.selected_projects && tailored_data.selected_projects.length > 0) {
    docChildren.push(createSectionHeader("PROJECTS"));
    tailored_data.selected_projects.forEach((projName) => {
        const profileProj = (profile_dict.projects || []).find(p => p.name === projName);
        if (profileProj) {
            const tech = profileProj.tech_stack ? profileProj.tech_stack.join(", ") : "";
            const titleLeft = `${projName} | ${tech}`;
            const rightText = profileProj.github_url ? profileProj.github_url : '';
            
            docChildren.push(createTwoColumnRow(titleLeft, rightText, true));
            
            if (profileProj.description) {
                docChildren.push(createBullet(profileProj.description));
            }
            if (profileProj.impact) {
                docChildren.push(createBullet(profileProj.impact));
            }
        }
    });
}

// SKILLS
if (tailored_data.selected_skills && Object.keys(tailored_data.selected_skills).length > 0) {
    docChildren.push(createSectionHeader("TECHNICAL SKILLS"));
    Object.entries(tailored_data.selected_skills).forEach(([category, skills]) => {
        if (skills && skills.length > 0) {
            docChildren.push(new docx.Paragraph({
                children: [
                    new docx.TextRun({
                        text: `${category.charAt(0).toUpperCase() + category.slice(1)}: `,
                        bold: true,
                        size: 19
                    }),
                    new docx.TextRun({
                        text: skills.join(", "),
                        size: 19
                    })
                ],
                bullet: { level: 0 },
                spacing: { before: 40, after: 40 }
            }));
        }
    });
}

// EDUCATION
if (profile_dict.education && profile_dict.education.length > 0) {
    docChildren.push(createSectionHeader("EDUCATION"));
    profile_dict.education.forEach((edu) => {
        const titleLeft = `${edu.degree || ''} — ${edu.institution || ''}`;
        const dates = (edu.year_start || edu.year_end) ? `${edu.year_start || ''} – ${edu.year_end || ''}` : '';
        
        docChildren.push(createTwoColumnRow(titleLeft, dates, true));
        
        const gpa = edu.gpa ? `CGPA: ${edu.gpa}` : '';
        if (gpa) {
            docChildren.push(new docx.Paragraph({
                children: [new docx.TextRun({ text: gpa, size: 19 })],
                spacing: { before: 40, after: 40 }
            }));
        }
    });
}

const doc = new docx.Document({
    sections: [{
        properties: {
            page: {
                margin: {
                    top: docx.convertInchesToTwip(0.6),
                    right: docx.convertInchesToTwip(0.6),
                    bottom: docx.convertInchesToTwip(0.6),
                    left: docx.convertInchesToTwip(0.6),
                },
                size: {
                    width: docx.convertInchesToTwip(8.5),
                    height: docx.convertInchesToTwip(11),
                }
            }
        },
        children: docChildren
    }],
    styles: {
        default: {
            document: {
                run: {
                    font: "Calibri",
                },
            },
        },
    }
});

docx.Packer.toBuffer(doc).then((buffer) => {
    fs.writeFileSync(outputFile, buffer);
    console.log(`Successfully created ${outputFile}`);
}).catch((err) => {
    console.error("Error creating docx", err);
    process.exit(1);
});

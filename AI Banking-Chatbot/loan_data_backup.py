
# Official bank loan information for the chatbot.
# Last reviewed: 21 October 2026.
# Rates are indicative and must be verified against current
# official bank terms before being presented as current offers.

BANK_LOAN_DATA = {
    "SBI": {
        "home loan": {
            "rate_display": "7.25% p.a. onwards",
            "emi_rate": 7.25,
            "effective_period": "Effective from 1 April 2026",
            "tenure": None,
            "source": (
                "https://sbi.bank.in/web/interest-rates/"
                "interest-rates/loan-schemes-interest-rates"
            ),
        },
    },
    "personal loan": {
    "rate_display": "10.05% p.a. onwards; verify current rate",
    "effective_period": "Verify current official rate before applying",
    "tenure": "6–84 months",
    "eligibility": (
        "Salaried government, defence or corporate employees with "
        "an SBI Salary Package Account. Age generally 21–60 years. "
        "Minimum service: 6 months for government/defence employees "
        "and 12 months for corporate employees. Minimum net monthly "
        "salary: ₹20,000 for government/defence and ₹25,000 for "
        "corporate employees. Credit assessment applies."
    ),
    "documents_salaried": (
        "Application form and photograph; PAN; one officially valid "
        "document; six months of salary slips; six months of the "
        "salary-account statement; latest ITR/Form 16 where applicable."
    ),
    "documents_self_employed": (
        "This SBI product is described for salaried employees; "
        "check SBI for an applicable self-employed loan product."
    ),
    "source": (
        "https://sbi.co.in/web/personal-banking/loans/"
        "personal-loans/sbi-personal-loan"
    ),
},

    "ICICI Bank": {
        "personal loan": {
    "rate_display": "9.99%–16.50% p.a.; verify current offer",
    "effective_period": "Verify current official rate and eligibility",
    "tenure": "12–72 months",
    "eligibility": (
        "Eligibility depends on age, income, employment, credit "
        "history and repayment capacity. The bank publishes "
        "different criteria for salaried and self-employed applicants; "
        "minimum income and experience requirements can vary by profile."
    ),
    "documents_salaried": (
        "PAN; identity and address proof; recent salary slips; "
        "recent bank statements showing salary credits; photographs "
        "or other documents if requested by the bank."
    ),
    "documents_self_employed": (
        "PAN and KYC documents; bank statements; income proof such "
        "as ITR or financial statements; business and office-address "
        "proof where applicable."
    ),
    "source": (
        "https://www.icici.bank.in/personal-banking/loans/"
        "personal-loan/eligibility"
    ),
},
        "home loan": {
            "rate_display": (
                "7.55% p.a. onwards "
                "(eligible pre-approved loans; verify terms)"
            ),
            "emi_rate": 7.55,
            "effective_period": (
                "Verify current official terms and eligibility"
            ),
            "tenure": None,
            "source": (
                "https://www.icici.bank.in/personal-banking/loans/"
                "home-loan"
            ),
        },
    },

    "Axis Bank": {
        "personal loan": {
    "rate_display": "9.90%–21.50% p.a.; verify current rate",
    "effective_period": "Verify current official rate and eligibility",
    "tenure": "12–60 months",
    "eligibility": (
        "Eligibility depends on age, monthly income, employment "
        "stability, credit history and existing repayment obligations. "
        "Confirm the current minimum income, age limits and work "
        "experience requirements with Axis Bank."
    ),
    "documents_salaried": (
        "PAN and KYC documents; recent salary slips; bank statements "
        "showing salary credits; employment proof if requested."
    ),
    "documents_self_employed": (
        "Exact requirements not verified in configured data. Ask "
        "Axis Bank for its current self-employed applicant checklist."
    ),
    "source": "https://www.axis.bank.in/interest-rates-and-charges",
},
        "home loan": {
            "rate_display": (
                "8.00% p.a. onwards (verify eligible profiles)"
            ),
            "emi_rate": 8.00,
            "effective_period": (
                "Verify current official terms and eligibility"
            ),
            "tenure": None,
            "source": (
                "https://www.axis.bank.in/interest-rates-and-charges"
            ),
        },
    },

    "HDFC Bank": {
        "personal loan": {
    "rate_display": "9.99%–24.00% p.a.; verify current rate",
    "effective_period": "Verify current official rate and eligibility",
    "tenure": "Not verified in configured data",
    "eligibility": (
        "Eligibility and available offers depend on the applicant's "
        "profile and the bank's assessment. Confirm current age, "
        "income, employment and credit requirements with HDFC Bank."
    ),
    "documents_salaried": (
        "For applicants who are not pre-approved, the bank may request "
        "salary slips, employer details and KYC or income verification. "
        "Requirements depend on the application journey."
    ),
    "documents_self_employed": (
        "Exact requirements not verified in configured data. Confirm "
        "the current checklist with HDFC Bank."
    ),
    "source": "https://www.hdfc.bank.in/personal-loan/documentation",
},
        "home loan": {
            "rate_display": (
                "8.00% p.a. onwards (illustrative; verify current rate)"
            ),
            "emi_rate": 8.00,
            "effective_period": (
                "Verify current official terms and eligibility"
            ),
            "tenure": None,
            "source": (
                "https://www.hdfc.bank.in/home-loan"
            ),
        },
    },

    "personal loan": {
    "rate_display": "10.99% p.a. onwards; verify current rate",
    "effective_period": "Verify current official rate and eligibility",
    "tenure": "Up to 72 months",
    "eligibility": (
        "Eligibility depends on age, income, employment profile, "
        "credit history and repayment capacity. Confirm current "
        "minimum income, work experience and age limits with Kotak."
    ),
    "documents_salaried": (
        "PAN and identity/address proof; recent salary slips; "
        "bank statements showing salary credits; other documents "
        "as required by the bank."
    ),
    "documents_self_employed": (
        "Exact requirements not verified in configured data. Confirm "
        "the current business-income and documentation checklist "
        "with Kotak Mahindra Bank."
    ),
    "source": (
        "https://www.kotak.bank.in/en/personal-banking/"
        "loans/personal-loan/interest-rates.html"
    ),
},
        "home loan": {
            "rate_display": (
                "7.60% p.a. onwards (verify current rate)"
            ),
            "emi_rate": 7.60,
            "effective_period": (
                "Verify current official terms and eligibility"
            ),
            "tenure": None,
            "source": (
                "https://www.kotak.bank.in/en/personal-banking/"
                "loans/home-loan/interest-rates.html"
            ),
        },
    },


# Repayment tenures from official bank product information.
# None means the tenure has not yet been verified for this product.
# These are product-specific limits, not guaranteed approvals.

BANK_LOAN_TENURES = {
    "SBI": {
        "personal loan": {
            "tenure": "6–84 months",
            "source": (
                "https://sbi.co.in/web/personal-banking/loans/"
                "personal-loans/sbi-personal-loan"
            ),
        },
        "education loan": {
            "tenure": (
                "Up to 15 years after the course period and "
                "applicable repayment holiday, under the cited scheme"
            ),
            "source": (
                "https://sbi.co.in/web/personal-banking/loans/"
                "education-loans/student-loan-scheme"
            ),
        },
        "car loan": {
            "tenure": (
                "3–7 years under the SBI Assured Car Loan scheme"
            ),
            "source": (
                "https://sbi.co.in/web/personal-banking/loans/"
                "auto-loans/sbi-assured-car-loan-scheme"
            ),
        },
        "home loan": {
            "tenure": "Up to 30 years, subject to age and scheme conditions",
            "source": (
                "https://www.sbi.co.in/web/personal-banking/loans/"
                "home-loans"
            ),
        },
    },

    "ICICI Bank": {
        "personal loan": {
            "tenure": "12–72 months",
            "source": (
                "https://www.icici.bank.in/personal-banking/loans/"
                "personal-loan"
            ),
        },
        "home loan": {
            "tenure": "Up to 30 years, subject to eligibility",
            "source": (
                "https://www.icici.bank.in/personal-banking/loans/"
                "home-loan"
            ),
        },
        "education loan": {
            "tenure": (
                "Up to 15 years, including course period, "
                "for the cited collateral-free product"
            ),
            "source": (
                "https://www.icici.bank.in/personal-banking/loans/"
                "education-loan/instant-education-loan"
            ),
        },
        "car loan": {
            "tenure": "12–84 months",
            "source": (
                "https://www.icici.bank.in/personal-banking/loans/"
                "car-loan"
            ),
        },
    },

    "Axis Bank": {
        "personal loan": {
            "tenure": "12–60 months",
            "source": (
                "https://www.axis.bank.in/blogs/personal-loan/"
                "minimum-and-maximum-personal-loan-tenure"
            ),
        },
        "home loan": {
            "tenure": "Up to 30 years, subject to eligibility",
            "source": (
                "https://www.axis.bank.in/blogs/home-loan/"
                "minimum-and-maximum-tenure-for-home-loans"
            ),
        },
        "education loan": {
            "tenure": (
                "Up to 15 years for specified Prime schemes; "
                "other schemes may differ"
            ),
            "source": (
                "https://www.axis.bank.in/loans/education-loan"
            ),
        },
        "car loan": {
            "tenure": "1–7 years for eligible new-car loans",
            "source": (
                "https://www.axis.bank.in/loans/car-loan"
            ),
        },
    },

    "HDFC Bank": {
        "education loan": {
            "tenure": (
                "Up to 15 years, including the applicable moratorium"
            ),
            "source": (
                "https://www.hdfc.bank.in/education-loan"
            ),
        },
        "car loan": {
            "tenure": (
                "Up to 8 years for eligible EV loans; "
                "other car products may differ"
            ),
            "source": (
                "https://www.hdfc.bank.in/car-loan"
            ),
        },
        "personal loan": {
            "tenure": None,
            "source": None,
        },
        "home loan": {
            "tenure": None,
            "source": None,
        },
    },

    "Kotak Mahindra Bank": {
        "personal loan": {
            "tenure": "Up to 72 months",
            "source": (
                "https://www.kotak.bank.in/en/personal-banking/"
                "loans/personal-loan.html"
            ),
        },
        "home loan": {
            "tenure": "Up to 20 years, subject to eligibility",
            "source": (
                "https://www.kotak.bank.in/en/personal-banking/"
                "loans/home-loan/home-loan-faqs.html"
            ),
        },
        "car loan": {
            "tenure": "12–84 months under the cited product",
            "source": (
                "https://www.kotak.bank.in/en/personal-banking/"
                "loans/car-loan.html"
            ),
        },
        "education loan": {
            "tenure": None,
            "source": None,
        },
    },
}

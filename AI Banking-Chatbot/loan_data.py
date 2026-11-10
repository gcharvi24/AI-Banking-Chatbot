
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
            "source": "https://sbi.bank.in/web/interest-rates/interest-rates/loan-schemes-interest-rates",
        },
        "personal loan": {
            "rate_display": "Not verified; check current official rate",
            "effective_period": "Verify current official rate before applying",
            "tenure": "6–84 months",
            "eligibility": (
                "Salaried government, defence or corporate employees "
                "with an eligible SBI Salary Package Account. Age, "
                "salary and service requirements depend on the scheme."
            ),
            "documents_salaried": (
                "Application form, PAN, identity proof, salary slips, "
                "salary-account statements and income documents as "
                "required by SBI."
            ),
            "documents_self_employed": (
                "Check SBI for a suitable product and its current "
                "documentation requirements."
            ),
            "source": "https://sbi.co.in/web/personal-banking/loans/personal-loans/sbi-personal-loan",
        },
    },
    "ICICI Bank": {
        "personal loan": {
            "rate_display": "9.99%–16.50% p.a.; verify current offer",
            "effective_period": "Verify current official rate",
            "tenure": "12–72 months",
            "eligibility": (
                "Depends on age, income, employment, credit history "
                "and repayment capacity. Requirements vary by profile."
            ),
            "documents_salaried": (
                "PAN, identity/address proof, recent salary slips "
                "and bank statements showing salary credits."
            ),
            "documents_self_employed": (
                "PAN, KYC documents, bank statements and applicable "
                "income, tax and business documents."
            ),
            "source": "https://www.icici.bank.in/personal-banking/loans/personal-loan/personal-loan-interest-rates",
        },
        "home loan": {
            "rate_display": "7.55% p.a. onwards; verify current terms",
            "emi_rate": 7.55,
            "effective_period": "Verify current official terms",
            "tenure": None,
            "source": "https://www.icici.bank.in/personal-banking/loans/home-loan",
        },
    },
    "Axis Bank": {
        "personal loan": {
            "rate_display": "9.90%–21.50% p.a.; verify current rate",
            "effective_period": "Verify current official rate",
            "tenure": "12–60 months",
            "eligibility": (
                "Depends on age, income, employment stability, credit "
                "history and existing repayment obligations."
            ),
            "documents_salaried": (
                "PAN, KYC documents, recent salary slips and bank "
                "statements showing salary credits."
            ),
            "documents_self_employed": (
                "Confirm the current self-employed applicant checklist "
                "with Axis Bank."
            ),
            "source": "https://www.axis.bank.in/interest-rates-and-charges",
        },
        "home loan": {
            "rate_display": "8.00% p.a. onwards; verify current rate",
            "emi_rate": 8.00,
            "effective_period": "Verify current official terms",
            "tenure": None,
            "source": "https://www.axis.bank.in/interest-rates-and-charges",
        },
    },
    "HDFC Bank": {
        "personal loan": {
            "rate_display": "9.99%–24.00% p.a.; verify current rate",
            "effective_period": "Verify current official rate",
            "tenure": None,
            "eligibility": (
                "Depends on applicant profile and bank assessment. "
                "Confirm current age, income, employment and credit "
                "requirements with HDFC Bank."
            ),
            "documents_salaried": (
                "KYC documents and income/employment evidence as "
                "required for the application."
            ),
            "documents_self_employed": (
                "Confirm the current business-income and documentation "
                "checklist with HDFC Bank."
            ),
            "source": "https://www.hdfc.bank.in/personal-loan/interest-rates-and-charges",
        },
        "home loan": {
            "rate_display": "8.00% p.a. onwards; verify current rate",
            "emi_rate": 8.00,
            "effective_period": "Verify current official terms",
            "tenure": None,
            "source": "https://www.hdfc.bank.in/home-loan",
        },
    },
    "Kotak Mahindra Bank": {
        "personal loan": {
            "rate_display": "10.99% p.a. onwards; verify current rate",
            "effective_period": "Verify current official rate",
            "tenure": "Up to 72 months",
            "eligibility": (
                "Depends on age, income, employment profile, credit "
                "history and repayment capacity."
            ),
            "documents_salaried": (
                "PAN, identity/address proof, recent salary slips "
                "and bank statements showing salary credits."
            ),
            "documents_self_employed": (
                "Confirm the current business-income and documentation "
                "checklist with Kotak Mahindra Bank."
            ),
            "source": "https://www.kotak.bank.in/en/personal-banking/loans/personal-loan/interest-rates.html",
        },
        "home loan": {
            "rate_display": "7.60% p.a. onwards; verify current rate",
            "emi_rate": 7.60,
            "effective_period": "Verify current official terms",
            "tenure": None,
            "source": "https://www.kotak.bank.in/en/personal-banking/loans/home-loan/interest-rates.html",
        },
    },
}

# Additional car and education loan interest-rate information.
# Rates depend on product, eligibility, credit profile and bank terms.

BANK_LOAN_DATA["SBI"]["car loan"] = {
    "rate_display": "8.85%–9.80% p.a. for new-car loans; verify current offer",
    "effective_period": "Check the current official rate page",
    "source": "https://sbi.bank.in/web/business/information/interest-rates",
}

BANK_LOAN_DATA["SBI"]["education loan"] = {
    "rate_display": (
        "9.40%–9.90% p.a. under the standard Student Loan Scheme; "
        "other schemes and concessions differ"
    ),
    "effective_period": "Rates effective from 9 June 2026; verify current terms",
    "source": (
        "https://sbi.bank.in/web/interest-rates/interest-rates/"
        "loan-schemes-interest-rates/education-loan-scheme"
    ),
}

BANK_LOAN_DATA["ICICI Bank"]["car loan"] = {
    "rate_display": (
        "Starting at 8.40% p.a. for eligible new-car loans; "
        "rates depend on product and applicant"
    ),
    "effective_period": "Effective from 1 June 2026; verify current offer",
    "source": (
        "https://www.icici.bank.in/personal-banking/loans/"
        "car-loan/interest-rate"
    ),
}

BANK_LOAN_DATA["ICICI Bank"]["education loan"] = {
    "rate_display": (
        "Starting at 8.50% p.a. for selected secured domestic courses; "
        "other courses and unsecured loans have different rates"
    ),
    "effective_period": "Verify current rate for the specific course and product",
    "source": (
        "https://www.icici.bank.in/personal-banking/loans/"
        "education-loan/interest-rates"
    ),
}

BANK_LOAN_DATA["Axis Bank"]["car loan"] = {
    "rate_display": "8.80%–11.70% p.a. for new-car loans; applicant-dependent",
    "effective_period": "Check the current official rate page",
    "source": "https://www.axis.bank.in/loans/car-loan/interest-rates-charges",
}

BANK_LOAN_DATA["Axis Bank"]["education loan"] = {
    "rate_display": (
        "13.00% p.a. listed on the official rate page; "
        "verify the applicable scheme and current rate"
    ),
    "effective_period": "Check the current official rate page",
    "source": "https://www.axis.bank.in/loans/education-loan",
}

BANK_LOAN_DATA["HDFC Bank"]["car loan"] = {
    "rate_display": "Starting at 8.25% p.a.; actual rate depends on eligibility",
    "effective_period": "Check the current official rate page",
    "source": "https://www.hdfc.bank.in/car-loan",
}

BANK_LOAN_DATA["HDFC Bank"]["education loan"] = {
    "rate_display": "Starting at 10.50% p.a.; terms and conditions apply",
    "effective_period": "Check the current official rate page",
    "source": "https://www.hdfc.bank.in/education-loan",
}

BANK_LOAN_DATA["Kotak Mahindra Bank"]["car loan"] = {
    "rate_display": (
        "Not numerically published on the linked product page; "
        "check the official lender for a current quote"
    ),
    "effective_period": "Applicant- and product-dependent",
    "source": (
        "https://www.kotak.bank.in/en/personal-banking/loans/"
        "car-loan.html"
    ),
}

BANK_LOAN_DATA["Kotak Mahindra Bank"]["education loan"] = {
    "rate_display": (
        "12.00% mean contracted rate reported for the quarter ended "
        "30 September 2026; this is a historical average, not an offer rate"
    ),
    "effective_period": "Quarter ended 30 September 2026; verify current offer",
    "source": "https://www.kotak.bank.in/en/rates/interest-rates.html",
}


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

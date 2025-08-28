deploy:
	./deploy.sh

run-jira-fetcher:
	oc delete job jira-issue-fetcher-manual || true
	oc create job jira-issue-fetcher-manual --from=cronjob/jira-issue-fetcher

.PHONY: deploy run-jira-fetcher
